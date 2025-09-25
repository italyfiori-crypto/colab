#!/usr/bin/env python3
"""
数据解析器
处理书籍、章节、词汇数据的解析、验证和比较
"""

import os
import json
import logging
import hashlib
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class DataParser:
    """数据解析和处理类"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def _calculate_file_md5(self, file_path: str) -> str:
        """计算文件MD5值"""
        if not os.path.exists(file_path):
            return ""
            
        hash_md5 = hashlib.md5()
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            self.logger.error(f"计算MD5失败 {file_path}: {e}")
            return ""
        
    def compare_data(self, new_data: Dict, existing_data: Dict, compare_fields: List[str]) -> Tuple[bool, List[str]]:
        """
        通用数据比较函数
        
        Args:
            new_data: 新数据
            existing_data: 现有数据
            compare_fields: 需要比较的字段列表
            
        Returns:
            (需要更新, 变化字段列表) 元组
        """
        if not existing_data:
            return True, ["new_record"]
            
        # 类型检查和转换
        if isinstance(existing_data, str):
            try:
                existing_data = json.loads(existing_data)
            except json.JSONDecodeError:
                return True, ["data_parse_error"]
        
        if not isinstance(existing_data, dict):
            return True, ["data_format_error"]
        
        changed_fields = []
        
        for field in compare_fields:
            new_value = new_data.get(field, '')
            existing_value = existing_data.get(field, '')
            
            # 转换为字符串进行比较，避免类型问题
            new_str = str(new_value).strip()
            existing_str = str(existing_value).strip()
            if new_str != existing_str:
                changed_fields.append(field)
        
        needs_update = len(changed_fields) > 0
        return needs_update, changed_fields

    def compare_book_data(self, new_data: Dict, existing_data: Dict) -> Tuple[bool, List[str]]:
        """比较书籍数据"""
        compare_fields = [
            'title', 'author', 'description', 'category', 
            'total_chapters', 'total_duration', 'is_active', 
            'cover_md5', 'tags'
        ]
        needs_update, changed_fields = self.compare_data(new_data, existing_data, compare_fields)

        if existing_data and not existing_data.get('cover_url'):
            needs_update = True
            changed_fields.append('cover_url')

        return needs_update, changed_fields

    def compare_chapter_data(self, new_data: Dict, existing_data: Dict) -> Tuple[bool, List[str]]:
        """比较章节数据"""
        compare_fields = [
            'title', 'duration', 'is_active', 
            'audio_md5', 'subtitle_md5', 'analysis_md5', 'chapter_number'
        ]

        needs_update, changed_fields = self.compare_data(new_data, existing_data, compare_fields)
        
        if existing_data and not existing_data.get('audio_url'):
            needs_update = True
            changed_fields.append('audio_url')
        if existing_data and not existing_data.get('subtitle_url'):
            needs_update = True
            changed_fields.append('subtitle_url')
        if existing_data and not existing_data.get('analysis_url'):
            needs_update = True
            changed_fields.append('analysis_url')

        return needs_update, changed_fields

    def parse_book_data(self, book_dir: str, book_id: str) -> Tuple[Dict, List[Dict]]:
        """解析单本书的数据"""
        meta_file = os.path.join(book_dir, "meta.json")
        
        if not os.path.exists(meta_file):
            raise FileNotFoundError(f"书籍元数据文件不存在: {meta_file}")
        
        # 读取书籍元数据
        with open(meta_file, 'r', encoding='utf-8') as f:
            meta_data = json.load(f)
        
        
        # 解析章节数据（从meta.json中的chapters数组）
        chapters_data = []
        chapters_info = meta_data.get('chapters', [])
        
        for i, chapter_info in enumerate(chapters_info):
            # 计算音频和字幕文件MD5
            audio_file_path = os.path.join(book_dir, chapter_info.get('local_audio_file', ''))
            audio_md5 = self._calculate_file_md5(audio_file_path)
            
            subtitle_file_path = os.path.join(book_dir, chapter_info.get('local_subtitle_file', ''))
            subtitle_md5 = self._calculate_file_md5(subtitle_file_path)
            
            # 从音频文件路径提取子章节文件名作为ID
            audio_filename = os.path.basename(chapter_info.get('local_audio_file', ''))
            subchapter_name = os.path.splitext(audio_filename)[0]  # 去掉扩展名
            
            # 计算字幕解析文件MD5
            analysis_file_path = os.path.join(book_dir, chapter_info.get('local_analysis_file', ''))
            analysis_md5 = self._calculate_file_md5(analysis_file_path)
            
            chapter_data = {
                '_id': f"{book_id}_{subchapter_name}",
                'book_id': book_id,
                'chapter_number': chapter_info['chapter_number'],
                'title': chapter_info['title_cn'] or chapter_info['title'],
                'duration': int(chapter_info['duration']) if chapter_info['duration'] else 0,
                'is_active': True,
                'audio_url': '',  # 稍后上传音频后填充
                'audio_md5': audio_md5,
                'subtitle_url': '',  # 稍后上传字幕后填充
                'subtitle_md5': subtitle_md5,
                'analysis_url': '',  # 稍后上传字幕解析文件后填充
                'analysis_md5': analysis_md5,
                'local_audio_file': audio_file_path,
                'local_subtitle_file': subtitle_file_path,
                'local_analysis_file': analysis_file_path,
                'created_at': int(time.time() * 1000),
                'updated_at': int(time.time() * 1000)
            }
            
            chapters_data.append(chapter_data)
        
        # 从meta.json解析书籍信息
        book_info = meta_data['book']
        
        # 计算封面文件MD5
        cover_file_path = os.path.join(book_dir, book_info.get('local_cover_file', ''))
        cover_md5 = self._calculate_file_md5(cover_file_path)
        
        # 构建书籍数据
        book_data = {
            '_id': book_id,
            'title': book_info['title'],
            'author': book_info.get('author', ''),
            'cover_url': '',  # 稍后上传封面后填充
            'cover_md5': cover_md5,
            'category': book_info.get('category', ''),
            'description': book_info.get('description', ''),
            'total_chapters': book_info.get('total_chapters', 0),
            'total_duration': int(book_info.get('total_duration', 0)),
            'is_active': True,
            'tags': book_info.get('tags', []),
            'local_cover_file': cover_file_path,
            'created_at': int(time.time() * 1000),
            'updated_at': int(time.time() * 1000),
            'done': book_info.get('done', False)
        }
        
        return book_data, chapters_data
