#!/usr/bin/env python3
"""
词汇上传服务
处理词汇表和章节词汇关联的上传逻辑
"""

import os
import json
import time
import logging
from datetime import datetime
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
        
        # 音频上传配置
        self.audio_cloud_path_prefix = "vocabulary/audio/"
        self.audio_format = "wav"  # 使用AudioGenerator生成的wav格式
        
    def upload_vocabularies(self, book_dir: Path, book_id: str) -> bool:
        """上传当前书籍的词汇数据和音频文件"""
        try:
            # 获取词汇总表路径
            master_vocab_path = os.path.join(self.program_root, "output", "vocabulary", "master_vocabulary.json")
            
            if not os.path.exists(master_vocab_path):
                self.logger.error(f"词汇总表不存在: {master_vocab_path}")
                return False
            
            # 加载汇总词典（已经是数据库格式）
            raw_master_vocab = self._load_master_vocabulary(master_vocab_path)
            
            # 收集当前书籍的所有单词
            book_words = self._collect_book_words(book_dir)
            
            if not book_words:
                self.logger.info("没有词汇需要上传")
                return True
            
            # 过滤出当前书籍的词汇数据
            book_vocabulary_data = {word: raw_master_vocab[word] 
                                  for word in book_words 
                                  if word in raw_master_vocab}
            
            if not book_vocabulary_data:
                self.logger.info("没有匹配的词汇数据")
                return True
            
            # 找出需要完整处理的单词（用uploaded判断）
            words_to_process = [word for word in book_vocabulary_data.keys() 
                              if not book_vocabulary_data[word].get("uploaded")]
            
            if not words_to_process:
                self.logger.info("所有词汇都已完全处理，跳过上传")
                return True
            
            self.logger.info(f"开始处理 {len(words_to_process)} 个词汇（数据库+音频）...")
            
            success_count = 0
            for idx, word in enumerate(words_to_process):
                try:
                    # 获取词汇数据（已经是数据库格式）
                    db_word_data = book_vocabulary_data[word]
                    
                    # 步骤1：上传词汇数据到数据库
                    db_success = self._insert_word_with_retry(db_word_data)
                    
                    if not db_success:
                        self.logger.error(f"词汇数据库写入失败: {word}")
                        continue
                    
                    # 步骤2：上传音频文件到云存储
                    audio_success, cloud_file_id = self._upload_word_audio(word)
                    
                    if not audio_success:
                        self.logger.error(f"音频上传失败: {word}")
                        continue
                    
                    # 步骤3：只有两步都成功，才在词典中标记完成
                    raw_master_vocab[word]["audio_url"] = cloud_file_id
                    raw_master_vocab[word]["uploaded"] = True
                    
                    success_count += 1
                    self.logger.info(f"完整处理成功: {word}")
                    
                except Exception as e:
                    self.logger.error(f"处理词汇失败 {word}: {e}")
                    continue
                
                # 每10个单词显示一次进度
                if (idx + 1) % 10 == 0:
                    self.logger.info(f"📝 进度: {idx + 1}/{len(words_to_process)}, 成功: {success_count}")
            
            # 保存更新的词汇表
            if success_count > 0:
                self._save_master_vocabulary(raw_master_vocab, master_vocab_path)
            
            self.logger.info(f"词汇处理完成: 成功 {success_count}, 总计 {len(book_vocabulary_data)} 个")
            return True
            
        except Exception as e:
            self.logger.error(f"词汇上传失败: {e}")
            return False

    def upload_chapter_vocabularies(self, book_dir: Path, book_id: str, vocabulary_data: Dict) -> bool:
        """上传章节词汇关联数据"""
        try:
            vocab_subchapters_dir = os.path.join(book_dir, "vocabulary")
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
                        "created_at": datetime.now().isoformat()
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

    def _upload_word_audio(self, word: str) -> Tuple[bool, str]:
        """
        上传单个词汇的音频文件
        
        Args:
            word: 单词
            
        Returns:
            (是否上传成功, 云文件ID)
        """
        try:
            # 获取本地音频文件路径
            audio_dir = os.path.join(self.program_root, "output", "vocabulary", "compressed_audio")
            audio_file_path = os.path.join(audio_dir, f"{word}.{self.audio_format}")
            
            if not os.path.exists(audio_file_path):
                self.logger.error(f"本地音频文件不存在: {word}.{self.audio_format}")
                return False, ""
            
            # 上传到云存储
            cloud_path = f"{self.audio_cloud_path_prefix}{word}.{self.audio_format}"
            file_id = self.api.upload_file(audio_file_path, cloud_path)
            
            if file_id:
                return True, file_id
            else:
                return False, ""
                
        except Exception as e:
            self.logger.error(f"音频上传异常 {word}: {e}")
            return False, ""

    def _load_master_vocabulary(self, master_vocab_path: str) -> Dict[str, Dict]:
        """加载总词汇表（数据库格式）"""
        if not os.path.exists(master_vocab_path):
            return {}
        
        try:
            vocabulary = {}
            with open(master_vocab_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        word_data = json.loads(line.strip())
                        vocabulary[word_data['word']] = word_data
            return vocabulary
        except Exception as e:
            self.logger.error(f"加载总词汇表失败: {e}")
            return {}

    def _save_master_vocabulary(self, vocabulary: Dict[str, Dict], master_vocab_path: str):
        """保存总词汇表（数据库格式）"""
        os.makedirs(os.path.dirname(master_vocab_path), exist_ok=True)
        
        # 按单词字母排序
        sorted_vocab = dict(sorted(vocabulary.items()))
        
        # 输出格式：每行一个单词的JSON字符串（数据库格式）
        with open(master_vocab_path, 'w', encoding='utf-8') as f:
            for word, word_info in sorted_vocab.items():
                json_line = json.dumps(word_info, ensure_ascii=False, separators=(',', ':'))
                f.write(json_line + '\n')

