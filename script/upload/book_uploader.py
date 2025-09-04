#!/usr/bin/env python3
"""
书籍上传服务
处理书籍和章节的上传逻辑
"""

import os
import time
import logging
from typing import Dict, List
from wechat_api import WeChatCloudAPI
from data_parser import DataParser


class BookUploader:
    """书籍上传服务类"""
    
    def __init__(self, api_client: WeChatCloudAPI, program_root: str):
        self.api = api_client
        self.parser = DataParser(program_root)
        self.logger = logging.getLogger(__name__)
        self.program_root = program_root
        
    def upload_book_cover(self, book_dir: str, book_id: str, book_data: Dict) -> str:
        """上传书籍封面"""
        cover_file_path = os.path.join(book_dir, book_data.get('local_cover_file', ''))
        if not book_data.get('local_cover_file', '') or not os.path.exists(cover_file_path):
            return ""
            
        cloud_path = f"books/{book_id}/cover.jpg"
        file_id = self.api.upload_file(cover_file_path, cloud_path)
        
        if file_id:
            return file_id
        return ""

    def upload_book_if_needed(self, book_dir: str, book_data: Dict, existing_book: Dict, changed_fields: List[str]) -> bool:
        """根据需要上传或更新书籍"""
        book_id = book_data["_id"]
        
        if not existing_book:
            # 新书籍，上传封面
            cover_file_id = self.upload_book_cover(book_dir, book_id, book_data)
            if cover_file_id:
                book_data["cover_url"] = cover_file_id
            return self.api.add_database_records('books', [book_data])
        elif changed_fields:
            # 更新现有书籍
            if 'cover_md5' in changed_fields:
                cover_file_id = self.upload_book_cover(book_dir, book_id, book_data)
                if cover_file_id:
                    book_data["cover_url"] = cover_file_id
                else:
                    book_data["cover_url"] = existing_book.get("cover_url", "")
            else:
                book_data["cover_url"] = existing_book.get("cover_url", "")
            
            # 更新数据库记录
            update_data = {field: book_data[field] for field in changed_fields if field in book_data}
            update_data["updated_at"] = book_data["updated_at"]
            
            return self.api.update_database_record('books', book_id, update_data)
        
        return True

    def upload_chapter_files(self, book_dir: str, book_id: str, chapter_data: Dict) -> bool:
        """上传章节音频和字幕文件"""
        chapter_id = chapter_data["chapter_id"]
        
        # 上传音频文件
        audio_file_path = os.path.join(book_dir, chapter_data.get('local_audio_file', ''))
        if chapter_data.get('local_audio_file', '') and os.path.exists(audio_file_path):
            audio_filename = os.path.basename(audio_file_path)
            cloud_audio_path = f"books/{book_id}/audio/{audio_filename}"
            audio_file_id = self.api.upload_file(audio_file_path, cloud_audio_path)
            if audio_file_id:
                chapter_data["audio_url"] = audio_file_id
        
        # 上传字幕文件
        subtitle_file_path = os.path.join(book_dir, chapter_data.get('local_subtitle_file', ''))
        if chapter_data.get('local_subtitle_file', '') and os.path.exists(subtitle_file_path):
            subtitle_filename = os.path.basename(subtitle_file_path)
            cloud_subtitle_path = f"books/{book_id}/subtitles/{subtitle_filename}"
            subtitle_file_id = self.api.upload_file(subtitle_file_path, cloud_subtitle_path)
            if subtitle_file_id:
                chapter_data["subtitle_url"] = subtitle_file_id
        
        return True

    def upload_chapter_if_needed(self, book_dir: str, book_id: str, chapter_data: Dict, existing_chapter: Dict, changed_fields: List[str]) -> bool:
        """根据需要上传或更新章节"""
        chapter_id = chapter_data["_id"]
        
        if not existing_chapter:
            # 新章节，上传文件
            self.upload_chapter_files(book_dir, book_id, chapter_data)
            return self.api.add_database_records('chapters', [chapter_data])
        elif changed_fields:
            # 更新现有章节
            if any(field in changed_fields for field in ['audio_md5', 'subtitle_md5']):
                self.upload_chapter_files(book_dir, book_id, chapter_data)
            
            # 更新数据库记录
            update_data = {field: chapter_data[field] for field in changed_fields if field in chapter_data}
            update_data["updated_at"] = chapter_data["updated_at"]
            
            return self.api.update_database_record('chapters', chapter_id, update_data)
        
        return True

    def process_single_chapter(self, book_dir: str, book_id: str, chapter_data: Dict, existing_chapters_dict: Dict, stats: Dict) -> bool:
        """处理单个章节"""
        chapter_id = chapter_data["_id"]
        chapter_title = chapter_data.get("title", chapter_id)
        existing_chapter = existing_chapters_dict.get(chapter_id)
        
        # 比较数据
        needs_update, changed_fields = self.parser.compare_chapter_data(chapter_data, existing_chapter)
        
        if needs_update:
            if not existing_chapter:
                self.logger.info(f"🆕 新章节: {chapter_title}")
            else:
                self.logger.info(f"🔄 更新章节: {chapter_title} (变化: {', '.join(changed_fields)})")
                
            success = self.upload_chapter_if_needed(book_dir, book_id, chapter_data, existing_chapter, changed_fields)
            if success:
                if not existing_chapter:
                    stats['chapters_added'] += 1
                    self.logger.info(f"✅ 章节新增成功: {chapter_title}")
                else:
                    stats['chapters_updated'] += 1
                    self.logger.info(f"✅ 章节更新成功: {chapter_title}")
                return True
            else:
                stats['chapters_failed'] += 1
                self.logger.error(f"❌ 章节处理失败: {chapter_title}")
                return False
        else:
            stats['chapters_skipped'] += 1
            self.logger.info(f"⏭️ 章节跳过: {chapter_title}")
            return True

    def cleanup_orphaned_chapters(self, book_id: str, local_chapter_ids: set, existing_chapters_dict: dict) -> bool:
        """清理孤立的章节数据"""
        success = True
        deleted_count = 0
        orphaned_chapters = [ch_id for ch_id in existing_chapters_dict.keys() if ch_id not in local_chapter_ids]
        
        if not orphaned_chapters:
            self.logger.info("✅ 无需清理章节")
            return True
            
        self.logger.info(f"🧹 开始清理 {len(orphaned_chapters)} 个孤立章节...")
        
        for chapter_id in orphaned_chapters:
            chapter_data = existing_chapters_dict[chapter_id]
            chapter_title = chapter_data.get('title', chapter_id)
            
            # 删除数据库记录
            if self.api.delete_database_record('chapters', chapter_id):
                deleted_count += 1
                self.logger.info(f"🗑️ 删除章节: {chapter_title}")
                
                # 删除云存储文件
                if chapter_data.get('audio_url'):
                    file_id = self.api.extract_file_id_from_url(chapter_data['audio_url'])
                    if file_id:
                        self.api.delete_cloud_file(file_id)
                
                if chapter_data.get('subtitle_url'):
                    file_id = self.api.extract_file_id_from_url(chapter_data['subtitle_url'])
                    if file_id:
                        self.api.delete_cloud_file(file_id)
            else:
                success = False
                self.logger.error(f"❌ 章节删除失败: {chapter_title}")

            if self.api.delete_database_record('chapter_vocabularies', chapter_id):
                self.logger.info(f"🗑️ 删除章节词汇: {chapter_title}")
        
        self.logger.info(f"✅ 清理完成，删除了 {deleted_count} 个章节")
        return success