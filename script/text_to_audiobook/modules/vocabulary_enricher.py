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
from concurrent.futures import ThreadPoolExecutor, as_completed
import random

from .ecdict_helper import ECDictHelper
from .audio_generator import AudioGenerator, AudioGeneratorConfig


def load_master_vocabulary(master_vocab_path: str) -> Dict[str, Dict]:
    """加载总词汇表 - 公共方法"""
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
        print(f"⚠️ 加载总词汇表失败: {e}")
        return {}


@dataclass
class VocabularyEnricherConfig:
    """词汇富化配置"""
    
    # Free Dictionary API配置（用于获取音频）
    dictionary_api_base: str = "https://api.dictionaryapi.dev/api/v2/entries/en"
    
    # 请求配置
    timeout: int = 30
    max_retries: int = 3
    batch_size: int = 10
    max_workers: int = 2  # 并发线程数


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
        
        # 使用ECDICT富化当前批次
        enriched_count = 0
        for word in new_words:
            print(f"  🔄 处理 {word}")
            word_info = self._get_word_ecdict_info(word)
            if word_info:
                master_vocab[word] = word_info
                enriched_count += 1
        
        # 保存更新的总词汇表（第2步完成）
        self._save_master_vocabulary(master_vocab, master_vocab_path)
        
        print(f"✅ ECDICT基础信息补充完成: 成功处理 {enriched_count}/{len(new_words)} 个新词汇")
        return True
    
    def enrich_vocabulary_with_audio(self, master_vocab_path: str, word_voice: str = "af_heart", word_speed: float = 0.8) -> bool:
        """
        为总词汇表中的所有词汇生成音频文件
        
        Args:
            master_vocab_path: 总词汇表文件路径
            word_voice: 单词音频声音模型
            word_speed: 单词音频语速
            
        Returns:
            是否处理成功
        """
        print(f"🔄 步骤3: 为词汇生成音频文件...")
        
        # 创建公共音频目录
        vocab_dir = os.path.dirname(master_vocab_path)
        audio_dir = os.path.join(vocab_dir, "audio")
        os.makedirs(audio_dir, exist_ok=True)
        
        # 加载总词汇表
        master_vocab = self._load_master_vocabulary(master_vocab_path)
        if not master_vocab:
            print("⚠️ 没有词汇需要补充音频")
            return True
        
        # 找出没有音频文件的词汇
        words_need_audio = []
        for word, info in master_vocab.items():
            audio_file_path = os.path.join(audio_dir, f"{word}.wav")
            if not os.path.exists(audio_file_path):
                words_need_audio.append(word)
        
        if not words_need_audio:
            print("✅ 所有词汇都已有本地音频文件")
            # 更新词汇表中的音频路径信息
            for word in master_vocab:
                audio_file_path = os.path.join(audio_dir, f"{word}.wav")
                if os.path.exists(audio_file_path):
                    master_vocab[word]["audio_file"] = f"vocabulary/audio/{word}.wav"
            self._save_master_vocabulary(master_vocab, master_vocab_path)
            return True
        
        print(f"📝 发现 {len(words_need_audio)} 个词汇需要生成音频文件")
        print(f"🔊 音频配置: 声音={word_voice}, 语速={word_speed}")
        
        # 创建AudioGenerator实例
        try:
            audio_config = AudioGeneratorConfig(voice=word_voice, speed=word_speed)
            audio_generator = AudioGenerator(audio_config)
        except Exception as e:
            print(f"❌ AudioGenerator初始化失败: {e}")
            return False
        
        # 生成单词音频
        audio_count = 0
        print(f"  🔄 开始生成单词音频...")
        
        for i, word in enumerate(words_need_audio, 1):
            try:
                audio_file_path = audio_generator.generate_word_audio(word, audio_dir, word_voice, word_speed)
                if audio_file_path:
                    # 保存相对路径到词汇表
                    relative_path = f"vocabulary/audio/{word}.wav"
                    master_vocab[word]["audio_file"] = relative_path
                    audio_count += 1
                    print(f"    ✅ {word}: 音频生成成功 ({i}/{len(words_need_audio)})")
                else:
                    print(f"    ❌ {word}: 音频生成失败")
            except Exception as e:
                print(f"    ❌ {word}: 生成异常 - {e}")
        
        # 保存最终的总词汇表（第3步完成）
        self._save_master_vocabulary(master_vocab, master_vocab_path)
        
        print(f"✅ 音频信息补充完成: 成功生成 {audio_count}/{len(words_need_audio)} 个词汇音频文件")
        return True
    
    def _get_word_ecdict_info(self, word: str) -> Optional[Dict]:
        """
        从ECDICT获取单词基础信息并直接转换为数据库格式
        
        Args:
            word: 要查询的单词
            
        Returns:
            数据库格式的单词信息字典，如果未找到返回None
        """
        from datetime import datetime
        
        try:            
            if not self.ecdict:
                print(f"    ❌ {word}: ECDICT未初始化")
                return None
            
            ecdict_info = self.ecdict.query_word(word)
            if ecdict_info:
                # 解析tags字符串为数组
                level_tags = ecdict_info.get("level", "")
                tags = level_tags.split() if level_tags else []
                
                # 解析translation字符串为对象数组
                translation_str = ecdict_info.get("translation", "")
                translation = self._parse_translation(translation_str)
                
                # 解析exchange字符串为对象数组
                exchange_str = ecdict_info.get("exchange", "")
                exchange = self._parse_exchange(exchange_str)
                
                # 直接构造数据库格式
                word_data = {
                    "_id": word,
                    "word": word,
                    "phonetic": ecdict_info.get("phonetic", ""),
                    "translation": translation,
                    "tags": tags,
                    "exchange": exchange,
                    "bnc": ecdict_info.get("bnc", 0),
                    "frq": ecdict_info.get("frq", 0),
                    "audio_url": "",  # 初始为空，下载音频后填入
                    "uploaded": False,  # 上传状态标识
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
                return word_data
            else:
                print(f"    ❌ {word}: ECDICT中未找到")
                return None
                
        except Exception as e:
            print(f"    ❌ {word}: ECDICT查询失败 - {e}")
            return None
    
    
    def _load_master_vocabulary(self, master_vocab_path: str) -> Dict[str, Dict]:
        """加载总词汇表"""
        return load_master_vocabulary(master_vocab_path)
    
    def _save_master_vocabulary(self, vocabulary: Dict[str, Dict], master_vocab_path: str):
        """保存总词汇表（数据库格式，无需转换）"""
        os.makedirs(os.path.dirname(master_vocab_path), exist_ok=True)
        
        # 按单词字母排序
        sorted_vocab = dict(sorted(vocabulary.items()))
        
        # 统计信息
        total_words = len(sorted_vocab)
        level_stats = {}
        
        # 输出格式：每行一个单词的JSON字符串（已经是数据库格式）
        with open(master_vocab_path, 'w', encoding='utf-8') as f:
            for word, word_info in sorted_vocab.items():
                # 统计标签（已经是数组格式）
                tags = word_info.get("tags", [])
                for tag in tags:
                    level_stats[tag] = level_stats.get(tag, 0) + 1
                if not tags:
                    level_stats["unknown"] = level_stats.get("unknown", 0) + 1
                
                json_line = json.dumps(word_info, ensure_ascii=False, separators=(',', ':'))
                f.write(json_line + '\n')
        
        print(f"💾 总词汇表已保存: {master_vocab_path}")
        print(f"📊 词汇统计: 总计{total_words}词")
        
        # 按标签显示统计信息
        if level_stats:
            print("  标签分布:")
            for tag, count in sorted(level_stats.items()):
                print(f"    {tag}: {count}词")

    def _parse_translation(self, translation_str: str) -> List[Dict]:
        """解析翻译字符串为对象数组"""
        if not translation_str:
            return []
            
        translations = []
        parts = translation_str.split('\\n')
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
                
            import re
            match = re.match(r'^([a-z]+\.)\s*(.+)$', part)
            if match:
                pos_type = match.group(1)
                meaning = match.group(2)
                translations.append({
                    'type': pos_type,
                    'meaning': meaning,
                    'example': ''
                })
            else:
                translations.append({
                    'type': '',
                    'meaning': part,
                    'example': ''
                })
                
        return translations

    def _parse_exchange(self, exchange_str: str) -> List[Dict]:
        """解析词形变化字符串为对象数组"""
        if not exchange_str:
            return []
            
        exchanges = []
        if ':' in exchange_str:
            parts = exchange_str.split('/')
            for part in parts:
                if ':' in part:
                    type_code, form = part.split(':', 1)
                    exchanges.append({
                        'type': type_code.strip(),
                        'form': form.strip()
                    })
        
        return exchanges