#!/usr/bin/env python3
"""
词汇上传服务
处理词汇表和章节词汇关联的上传逻辑
"""

import os
import json
import time
import logging
from typing import Dict, List
from pathlib import Path
from wechat_api import WeChatCloudAPI
from data_parser import DataParser


class VocabularyUploader:
    """词汇上传服务类"""
    
    def __init__(self, api_client: WeChatCloudAPI):
        self.api = api_client
        self.parser = DataParser()
        self.logger = logging.getLogger(__name__)
        
        # 获取项目根目录
        self.program_root = os.path.dirname(os.path.dirname(__file__))
        
    def upload_vocabularies(self, book_dir: Path, book_id: str) -> bool:
        """上传当前书籍的词汇数据"""
        try:
            # 获取词汇总表路径（使用原始脚本的路径）
            master_vocab_path = os.path.join(self.program_root, "output", "vocabulary", "master_vocabulary.json")
            
            if not os.path.exists(master_vocab_path):
                self.logger.error(f"词汇总表不存在: {master_vocab_path}")
                return False
            
            # 解析词汇总表
            master_vocabulary_data = self.parser.parse_vocabulary_data(master_vocab_path)
            
            # 收集当前书籍的所有单词
            book_words = self._collect_book_words(book_dir)
            
            if not book_words:
                self.logger.info("没有词汇需要上传")
                return True
            
            # 过滤出当前书籍的词汇数据
            book_vocabulary_data = {word: master_vocabulary_data[word] 
                                  for word in book_words 
                                  if word in master_vocabulary_data}
            
            if not book_vocabulary_data:
                self.logger.info("没有匹配的词汇数据")
                return True
            
            # 逐个处理单词
            success_count = 0
            skip_count = 0
            filtered_words = list(book_vocabulary_data.values())
            
            self.logger.info(f"开始处理 {len(filtered_words)} 个词汇...")
            
            for idx, word_data in enumerate(filtered_words):
                word = word_data['word']
                
                # 查询单词是否已存在
                existing_word = self.api.query_database('vocabularies', {'word': word}, limit=1)
                
                if existing_word:
                    skip_count += 1
                else:
                    # 插入新单词（包含重试机制）
                    if self._insert_word_with_retry(word_data):
                        success_count += 1
                    else:
                        self.logger.error(f"单词插入失败: {word}")
                
                # 每10个单词显示一次进度
                if (idx + 1) % 10 == 0:
                    self.logger.info(f"📝 进度: {idx + 1}/{len(filtered_words)}, 新增: {success_count}, 跳过: {skip_count}")
            
            self.logger.info(f"词汇上传完成: 新增 {success_count}, 跳过 {skip_count}")
            return True
            
        except Exception as e:
            self.logger.error(f"词汇上传失败: {e}")
            return False

    def upload_chapter_vocabularies(self, book_dir: Path, book_id: str, vocabulary_data: Dict) -> bool:
        """上传章节词汇关联数据"""
        try:
            vocab_subchapters_dir = book_dir / "vocabulary" / "subchapters"
            if not vocab_subchapters_dir.exists():
                return True
            
            # 获取当前书籍的单词顺序
            book_words = self._collect_book_words(book_dir)
            
            # 处理每个子章节的词汇文件
            for vocab_file in vocab_subchapters_dir.glob("*.json"):
                try:
                    with open(vocab_file, 'r', encoding='utf-8') as f:
                        vocab_data = json.load(f)
                    
                    subchapter_id = vocab_data.get("subchapter_id", vocab_file.stem)
                    chapter_words = vocab_data.get("words", [])
                    
                    if not chapter_words:
                        continue
                    
                    # 按照book_words的顺序排序章节单词
                    ordered_words = [word for word in book_words if word in chapter_words]
                    
                    chapter_vocab_record = {
                        "_id": f"{book_id}_{subchapter_id}",
                        "book_id": book_id,
                        "chapter_id": subchapter_id,
                        "words": ordered_words,
                        "created_at": vocabulary_data.get("created_at", "")
                    }
                    
                    # 检查是否已存在
                    existing_record = self.api.query_database('chapter_vocabularies', 
                                                            {'_id': chapter_vocab_record["_id"]}, limit=1)
                    
                    if not existing_record:
                        if not self.api.add_database_records('chapter_vocabularies', [chapter_vocab_record]):
                            self.logger.error(f"章节词汇插入失败: {subchapter_id}")
                            return False
                    
                except Exception as e:
                    self.logger.error(f"处理章节词汇文件失败 {vocab_file}: {e}")
                    continue
            
            return True
            
        except Exception as e:
            self.logger.error(f"章节词汇上传失败: {e}")
            return False

    def _collect_book_words(self, book_dir: Path) -> List[str]:
        """收集当前书籍的所有单词（按顺序）"""
        book_words = []
        vocab_subchapters_dir = book_dir / "vocabulary" / "subchapters"
        
        if not vocab_subchapters_dir.exists():
            return book_words
        
        # 按文件名排序处理章节词汇
        vocab_files = sorted(vocab_subchapters_dir.glob("*.json"))
        
        for vocab_file in vocab_files:
            try:
                with open(vocab_file, 'r', encoding='utf-8') as f:
                    vocab_data = json.load(f)
                
                chapter_words = vocab_data.get("words", [])
                for word in chapter_words:
                    if word not in book_words:
                        book_words.append(word)
                        
            except Exception as e:
                self.logger.error(f"读取章节词汇文件失败 {vocab_file}: {e}")
                continue
        
        return book_words

    def _insert_word_with_retry(self, word_data: Dict, max_retries: int = 3) -> bool:
        """插入单词（包含重试机制）"""
        word = word_data['word']
        
        for retry_count in range(max_retries):
            try:
                if self.api.add_database_records('vocabularies', [word_data]):
                    return True
                else:
                    if retry_count < max_retries - 1:
                        time.sleep(1)
                    
            except Exception as e:
                if retry_count < max_retries - 1:
                    time.sleep(2)
                else:
                    self.logger.error(f"单词插入失败: {word} - {e}")
                    
        return False