#!/usr/bin/env python3
"""
字幕解析信息上传服务
处理字幕AI解析数据的上传逻辑
"""

import os
import json
import time
import logging
from typing import Dict, List
from wechat_api import WeChatCloudAPI


class SubtitleAnalysisUploader:
    """字幕解析信息上传服务类"""
    
    def __init__(self, api_client: WeChatCloudAPI):
        self.api = api_client
        self.logger = logging.getLogger(__name__)
        
    def parse_analysis_file(self, analysis_file_path: str, book_id: str, chapter_id: str) -> List[Dict]:
        """解析字幕解析JSON文件"""
        try:
            with open(analysis_file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
            # 按行分割，每行是一个JSON对象
            analysis_records = []
            for line_num, line in enumerate(content.split('\n'), 1):
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    analysis_data_local = json.loads(line)

                    analysis_data = {
                        '_id': f"{book_id}-{chapter_id}-{analysis_data_local.get('subtitle_index')}",
                        'book_id': book_id,
                        'chapter_id': chapter_id,
                        'subtitle_index': analysis_data_local.get('subtitle_index'),
                        
                        'timestamp': analysis_data_local.get('timestamp'),
                        'english_text': analysis_data_local.get('english_text', ''),
                        'chinese_text': analysis_data_local.get('chinese_text', ''),

                        'sentence_structure': analysis_data_local.get('sentence_structure', ''),
                        'structure_explanation': analysis_data_local.get('structure_explanation', ''),
                        'key_words': analysis_data_local.get('key_words', []),
                        'fixed_phrases': analysis_data_local.get('fixed_phrases', []),
                        'colloquial_expression': analysis_data_local.get('colloquial_expression', []),

                        'created_at': int(time.time() * 1000),
                        'updated_at': int(time.time() * 1000),
                    }
                                        
                    analysis_records.append(analysis_data)
                    
                except json.JSONDecodeError as e:
                    self.logger.warning(f"⚠️ 跳过无效JSON行 {line_num}: {e}")
                    continue
                    
            return analysis_records
            
        except Exception as e:
            self.logger.error(f"❌ 解析字幕分析文件失败 {analysis_file_path}: {e}")
            return []
    
    def get_existing_analysis_records(self, book_id: str, chapter_id: str) -> Dict[int, Dict]:
        """获取现有的字幕解析记录"""
        try:
            existing_records = self.api.query_all_records('analysis', {
                'book_id': book_id,
                'chapter_id': chapter_id
            })
            return {record['subtitle_index']: record for record in existing_records}
        except Exception as e:
            self.logger.error(f"❌ 查询现有字幕解析记录失败: {e}")
            return {}
    
    def upload_analysis_records(self, book_id: str, chapter_id: str, analysis_records: List[Dict]) -> Dict:
        """上传字幕解析记录"""
        stats = {
            'added': 0,
            'updated': 0,
            'skipped': 0,
            'failed': 0
        }
        
        if not analysis_records:
            return stats
            
        # 获取现有记录
        existing_records = self.get_existing_analysis_records(book_id, chapter_id)
        
        # 分批处理记录
        batch_size = 1
        for i in range(0, len(analysis_records), batch_size):
            batch = analysis_records[i:i + batch_size]
            
            records_to_add = []
            records_to_update = []
            
            for record in batch:
                subtitle_index = record['subtitle_index']
                existing_record = existing_records.get(subtitle_index)
                
                if existing_record:
                    # 检查是否需要更新（比较关键字段）
                    if self._needs_update(record, existing_record):
                        record['updated_at'] = int(time.time() * 1000)
                        records_to_update.append(record)
                    else:
                        stats['skipped'] += 1
                else:
                    records_to_add.append(record)
            
            # 批量添加新记录
            if records_to_add:
                try:
                    if self.api.add_database_records('analysis', records_to_add):
                        stats['added'] += len(records_to_add)
                        self.logger.info(f"✅ 新增 {len(records_to_add)} 条字幕解析记录")
                    else:
                        stats['failed'] += len(records_to_add)
                        self.logger.error(f"❌ 新增字幕解析记录失败,records_to_add: {records_to_add}")
                except Exception as e:
                    stats['failed'] += len(records_to_add)
                    self.logger.error(f"❌ 新增字幕解析记录异常: {e}")
            
            # 批量更新现有记录
            for record in records_to_update:
                try:
                    if self.api.update_database_record('analysis', record['_id'], record):
                        stats['updated'] += 1
                    else:
                        stats['failed'] += 1
                        self.logger.error(f"❌ 更新字幕解析记录失败: {record['_id']}")
                except Exception as e:
                    stats['failed'] += 1
                    self.logger.error(f"❌ 更新字幕解析记录异常 {record['_id']}: {e}")
        
        return stats
    
    def _needs_update(self, new_record: Dict, existing_record: Dict) -> bool:
        """检查记录是否需要更新"""
        # 比较关键字段
        key_fields = ['timestamp', 'english_text', 'chinese_text', 'sentence_structure', 
                     'structure_explanation', 'key_words', 'fixed_phrases', 'colloquial_expression']
        
        for field in key_fields:
            new_value = new_record.get(field)
            existing_value = existing_record.get(field)

            # 对于存储为JSON字符串的字段，需要先解析再比较
            if field in ['key_words', 'fixed_phrases', 'colloquial_expression']:
                try:
                    new_value = json.loads(new_value) if isinstance(new_value, str) else new_value
                    existing_value = json.loads(existing_value) if isinstance(existing_value, str) else existing_value
                except json.JSONDecodeError:
                    self.logger.warning(f"⚠️ JSON解析失败，字段: {field}, new_value: {new_value}, existing_value: {existing_value}")
                    # 如果解析失败，则按原始值比较
                    pass

            if new_value != existing_value:
                return True
        return False
    
    def process_book_analysis(self, book_dir: str, book_id: str) -> Dict:
        """处理单本书的字幕解析上传"""
        analysis_dir = os.path.join(book_dir, 'analysis')
        
        if not os.path.exists(analysis_dir):
            self.logger.info(f"📝 书籍 {book_id} 没有字幕解析目录")
            return {'total_processed': 0}
        
        total_stats = {
            'files_processed': 0,
            'total_records': 0,
            'added': 0,
            'updated': 0,
            'skipped': 0,
            'failed': 0
        }
        
        # 遍历解析文件
        for filename in os.listdir(analysis_dir):
            if not filename.endswith('.json'):
                continue
                
            # 从文件名提取chapter_id (去掉.json后缀)
            chapter_id = os.path.splitext(filename)[0]
            analysis_file_path = os.path.join(analysis_dir, filename)
            
            self.logger.info(f"📝 处理字幕解析文件: {filename}")
            
            # 解析文件
            analysis_records = self.parse_analysis_file(analysis_file_path, book_id, chapter_id)
            
            if analysis_records:
                # 上传记录
                file_stats = self.upload_analysis_records(book_id, chapter_id, analysis_records)
                
                # 更新总统计
                total_stats['total_records'] += len(analysis_records)
                total_stats['added'] += file_stats['added']
                total_stats['updated'] += file_stats['updated']
                total_stats['skipped'] += file_stats['skipped']
                total_stats['failed'] += file_stats['failed']
                
                self.logger.info(f"📊 文件 {filename} 统计: 新增{file_stats['added']}, 更新{file_stats['updated']}, 跳过{file_stats['skipped']}, 失败{file_stats['failed']}")
            
            total_stats['files_processed'] += 1
        
        if total_stats['files_processed'] > 0:
            self.logger.info(f"✅ 书籍 {book_id} 字幕解析处理完成: 处理{total_stats['files_processed']}个文件, 共{total_stats['total_records']}条记录")
        
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