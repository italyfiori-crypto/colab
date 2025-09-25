#!/usr/bin/env python3
"""
字幕解析信息上传服务
通过云函数处理字幕AI解析数据的上传逻辑
"""

import logging
from typing import Dict
from wechat_api import WeChatCloudAPI


class SubtitleAnalysisUploader:
    """字幕解析信息上传服务类"""
    
    def __init__(self, api_client: WeChatCloudAPI):
        self.api = api_client
        self.logger = logging.getLogger(__name__)
    
    def process_book_analysis(self, book_dir: str, book_id: str) -> Dict:
        """处理单本书的字幕解析上传 - 通过云函数处理"""
        self.logger.info(f"📝 开始处理书籍 {book_id} 的字幕解析数据...")
        
        total_stats = {
            'files_processed': 0,
            'total_records': 0,
            'added': 0,
            'updated': 0,
            'skipped': 0,
            'failed': 0
        }
        
        # 从章节数据中获取已上传的解析文件信息
        # 这里需要获取章节信息来找到对应的analysis_url
        chapters = self.api.query_all_records('chapters', {'book_id': book_id})
        
        for chapter in chapters:
            analysis_url = chapter.get('analysis_url')
            chapter_id = chapter.get('chapter_id')
            
            if not analysis_url or not chapter_id:
                continue
            
            self.logger.info(f"📝 通过云函数处理章节 {chapter_id} 的字幕解析数据")
            
            # 通过云函数处理字幕解析文件
            file_stats = self.api.process_analysis_via_cloud_function(
                file_id=analysis_url,
                book_id=book_id, 
                chapter_id=chapter_id
            )
            
            # 更新总统计
            total_stats['total_records'] += file_stats.get('processed', 0)
            total_stats['added'] += file_stats.get('added', 0)
            total_stats['updated'] += file_stats.get('updated', 0)
            total_stats['skipped'] += file_stats.get('skipped', 0)
            total_stats['failed'] += file_stats.get('failed', 0)
            total_stats['files_processed'] += 1
            
            self.logger.info(f"📊 章节 {chapter_id} 统计: 处理{file_stats.get('processed', 0)}, 新增{file_stats.get('added', 0)}, 更新{file_stats.get('updated', 0)}, 跳过{file_stats.get('skipped', 0)}, 失败{file_stats.get('failed', 0)}")
        
        if total_stats['files_processed'] > 0:
            self.logger.info(f"✅ 书籍 {book_id} 字幕解析处理完成: 处理{total_stats['files_processed']}个文件, 共{total_stats['total_records']}条记录")
        else:
            self.logger.info(f"📝 书籍 {book_id} 没有字幕解析文件需要处理")
        
        return total_stats
    
    def cleanup_orphaned_analysis(self, book_id: str, existing_articles: set) -> bool:
        """清理孤立的字幕解析数据"""
        try:
            # 查询数据库中该书籍的所有解析记录
            existing_analysis = self.api.query_all_records('analysis', {'book_id': book_id})
            
            orphaned_records = []
            for record in existing_analysis:
                if record['chapter_id'] not in existing_articles:
                    orphaned_records.append(record['_id'])
            
            if not orphaned_records:
                self.logger.info(f"✅ 书籍 {book_id} 无需清理字幕解析数据")
                return True
            
            self.logger.info(f"🧹 清理书籍 {book_id} 的 {len(orphaned_records)} 条孤立字幕解析记录...")
            
            # 批量删除
            success_count = 0
            for record_id in orphaned_records:
                if self.api.delete_database_record('analysis', record_id):
                    success_count += 1
                    
            self.logger.info(f"✅ 成功清理 {success_count} 条孤立字幕解析记录")
            return success_count == len(orphaned_records)
            
        except Exception as e:
            self.logger.error(f"❌ 清理孤立字幕解析数据失败: {e}")
            return False