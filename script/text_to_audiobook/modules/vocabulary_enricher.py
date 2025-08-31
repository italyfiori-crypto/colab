#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
词汇富化模块
通过API获取单词的详细信息：音标、发音、释义、难度等级
"""

import os
import json
import time
import requests
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from pathlib import Path

from .ecdict_helper import ECDictHelper


@dataclass
class VocabularyEnricherConfig:
    """词汇富化配置"""
    
    # Free Dictionary API配置（用于获取音频）
    dictionary_api_base: str = "https://api.dictionaryapi.dev/api/v2/entries/en"
    
    # 请求配置
    timeout: int = 30
    max_retries: int = 3
    batch_size: int = 10


class VocabularyEnricher:
    """词汇富化器 - 为单词添加详细信息"""
    
    def __init__(self, config: VocabularyEnricherConfig):
        """
        初始化词汇富化器
        
        Args:
            config: 富化配置
        """
        self.config = config
        
        # 初始化ECDICT查询器
        try:
            self.ecdict = ECDictHelper()
        except Exception as e:
            print(f"⚠️ ECDICT初始化失败: {e}")
            print("📝 将使用API方式获取词汇信息")
            self.ecdict = None
        
        print("🔧 词汇富化器初始化完成")
    
    
    def enrich_vocabulary_with_ecdict(self, new_words: List[str], master_vocab_path: str) -> bool:
        """
        使用ECDICT为新词汇补充基础信息
        
        Args:
            new_words: 需要处理的新单词列表
            master_vocab_path: 总词汇表文件路径
            
        Returns:
            是否处理成功
        """
        if not new_words:
            print("📝 没有新词汇需要处理")
            return True
        
        print(f"🔄 步骤2: 使用ECDICT为 {len(new_words)} 个新词汇补充基础信息...")
        
        # 加载现有总词汇表
        master_vocab = self._load_master_vocabulary(master_vocab_path)
        
        # 批量处理新词汇
        enriched_count = 0
        for i in range(0, len(new_words), self.config.batch_size):
            batch = new_words[i:i + self.config.batch_size]
            batch_num = i // self.config.batch_size + 1
            total_batches = (len(new_words) + self.config.batch_size - 1) // self.config.batch_size
            
            print(f"  🔄 处理批次 {batch_num}/{total_batches} ({len(batch)} 个单词)")
            
            # 使用ECDICT富化当前批次
            for word in batch:
                word_info = self._get_word_ecdict_info(word)
                if word_info:
                    master_vocab[word] = word_info
                    enriched_count += 1
        
        # 保存更新的总词汇表（第2步完成）
        self._save_master_vocabulary(master_vocab, master_vocab_path)
        
        print(f"✅ ECDICT基础信息补充完成: 成功处理 {enriched_count}/{len(new_words)} 个新词汇")
        return True
    
    def enrich_vocabulary_with_audio(self, master_vocab_path: str) -> bool:
        """
        为总词汇表中的所有词汇补充音频URL
        
        Args:
            master_vocab_path: 总词汇表文件路径
            
        Returns:
            是否处理成功
        """
        print(f"🔄 步骤3: 为词汇补充音频信息...")
        
        # 加载总词汇表
        master_vocab = self._load_master_vocabulary(master_vocab_path)
        if not master_vocab:
            print("⚠️ 没有词汇需要补充音频")
            return True
        
        # 找出没有音频的词汇
        words_need_audio = [word for word, info in master_vocab.items() 
                           if not info.get("audio")]
        
        if not words_need_audio:
            print("✅ 所有词汇都已有音频信息")
            return True
        
        print(f"📝 发现 {len(words_need_audio)} 个词汇需要补充音频")
        
        # 批量获取音频URL
        audio_count = 0
        for i in range(0, len(words_need_audio), self.config.batch_size):
            batch = words_need_audio[i:i + self.config.batch_size]
            batch_num = i // self.config.batch_size + 1
            total_batches = (len(words_need_audio) + self.config.batch_size - 1) // self.config.batch_size
            
            print(f"  🔄 处理音频批次 {batch_num}/{total_batches} ({len(batch)} 个单词)")
            
            for word in batch:
                audio_url = self._get_audio_url(word)
                if audio_url:
                    master_vocab[word]["audio"] = audio_url
                    audio_count += 1
                    print(f"    ✅ {word}: 获取音频成功")
                else:
                    print(f"    ❌ {word}: 获取音频失败")
            
            # 避免API限流
            if i + self.config.batch_size < len(words_need_audio):
                time.sleep(0.5)
        
        # 保存最终的总词汇表（第3步完成）
        self._save_master_vocabulary(master_vocab, master_vocab_path)
        
        print(f"✅ 音频信息补充完成: 成功为 {audio_count}/{len(words_need_audio)} 个词汇获取音频")
        return True
    
    def _get_word_ecdict_info(self, word: str) -> Optional[Dict]:
        """
        从ECDICT获取单词基础信息（不包含音频）
        
        Args:
            word: 要查询的单词
            
        Returns:
            单词信息字典，如果未找到返回None
        """
        try:            
            if not self.ecdict:
                print(f"    ❌ {word}: ECDICT未初始化")
                return None
            
            ecdict_info = self.ecdict.query_word(word)
            if ecdict_info:
                level_tags = ecdict_info.get("level", "")
                level_display = level_tags if level_tags else "unknown"
                
                word_data = {
                    "word": word,
                    "phonetic": ecdict_info.get("phonetic", ""),
                    "translation": ecdict_info.get("translation", ""),
                    "tags": level_tags,
                    "audio": "",  # 第2步不获取音频
                    "bnc": ecdict_info.get("bnc", 0),
                    "frq": ecdict_info.get("frq", 0),
                    "exchange": ecdict_info.get("exchange", "")
                }
                return word_data
            else:
                print(f"    ❌ {word}: ECDICT中未找到")
                return None
                
        except Exception as e:
            print(f"    ❌ {word}: ECDICT查询失败 - {e}")
            return None
    
    def _get_audio_url(self, word: str) -> str:
        """获取单词音频URL（使用dictionaryapi）"""
        try:
            url = f"{self.config.dictionary_api_base}/{word}"
            response = requests.get(url, timeout=self.config.timeout)
            
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0:
                    entry = data[0]
                    
                    # 提取发音音频URL
                    if "phonetics" in entry and entry["phonetics"]:
                        for phonetic_entry in entry["phonetics"]:
                            if phonetic_entry.get("audio"):
                                return phonetic_entry["audio"]
                    
        except Exception as e:
            print(f"      ⚠️ 获取音频失败: {e}")
        
        return ""
    
    def _load_master_vocabulary(self, master_vocab_path: str) -> Dict[str, Dict]:
        """加载总词汇表"""
        if not os.path.exists(master_vocab_path):
            return {}
        
        try:
            with open(master_vocab_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('vocabulary', {})
        except Exception as e:
            print(f"⚠️ 加载总词汇表失败: {e}")
            return {}
    
    def _save_master_vocabulary(self, vocabulary: Dict[str, Dict], master_vocab_path: str):
        """保存总词汇表"""
        os.makedirs(os.path.dirname(master_vocab_path), exist_ok=True)
        
        # 按单词字母排序
        sorted_vocab = dict(sorted(vocabulary.items()))
        
        # 统计信息
        total_words = len(sorted_vocab)
        level_stats = {}
        
        for word_info in sorted_vocab.values():
            level_tags = word_info.get("tags", "")
            
            if not level_tags:
                level_stats["unknown"] = level_stats.get("unknown", 0) + 1
            else:
                # 处理多个标签的情况，按空格分割
                tags = level_tags.split()
                for tag in tags:
                    level_stats[tag] = level_stats.get(tag, 0) + 1
        
        # 输出格式改为每行一个单词的JSON字符串
        with open(master_vocab_path, 'w', encoding='utf-8') as f:
            for word, word_info in sorted_vocab.items():
                json_line = json.dumps(word_info, ensure_ascii=False, separators=(',', ':'))
                f.write(json_line + '\n')
        
        print(f"💾 总词汇表已保存: {master_vocab_path}")
        print(f"📊 词汇统计: 总计{total_words}词")
        
        # 按标签显示统计信息
        if level_stats:
            print("  标签分布:")
            for tag, count in sorted(level_stats.items()):
                print(f"    {tag}: {count}词")