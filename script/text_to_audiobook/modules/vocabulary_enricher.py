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
import re
from urllib.parse import urljoin
from bs4 import BeautifulSoup

from .ecdict_helper import ECDictHelper


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
    
    # Cambridge Dictionary配置
    cambridge_base_url: str = "https://dictionary.cambridge.org/dictionary/english"
    cambridge_audio_base: str = "https://dictionary.cambridge.org"
    
    # 请求配置
    timeout: int = 30
    max_retries: int = 3
    batch_size: int = 10
    max_workers: int = 2  # 并发线程数
    
    # 音频下载配置
    audio_download_dir: str = "audio"


class CambridgeDictionaryAPI:
    """剑桥词典API - 获取音标和音频"""
    
    def __init__(self, config: VocabularyEnricherConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def get_word_info(self, word: str) -> Optional[Dict]:
        """
        从剑桥词典获取单词信息
        
        Args:
            word: 要查询的单词
            
        Returns:
            包含音标和音频URL的字典，失败返回None
        """
        try:
            url = f"{self.config.cambridge_base_url}/{word}"
            response = self.session.get(url, timeout=self.config.timeout)
            
            if response.status_code != 200:
                print(f"    ❌ {word}: 剑桥词典请求失败 ({response.status_code})")
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 提取音标和音频信息
            phonetics = self._extract_phonetics(soup)
            audio_urls = self._extract_audio_urls(soup, word)
            
            if phonetics or audio_urls:
                return {
                    'phonetics': phonetics,
                    'audio_urls': audio_urls
                }
            else:
                print(f"    ❌ {word}: 未找到音标或音频信息")
                return None
                
        except Exception as e:
            print(f"    ❌ {word}: 剑桥词典查询异常 - {e}")
            return None
    
    def _extract_phonetics(self, soup: BeautifulSoup) -> Dict[str, str]:
        """提取音标信息"""
        phonetics = {}
        
        # 查找发音信息容器
        pron_containers = soup.find_all('span', class_='pron')
        
        for container in pron_containers:
            # 在容器内查找音标
            ipa_element = container.find('span', class_='ipa')
            if not ipa_element:
                continue
                
            phonetic_text = ipa_element.get_text(strip=True)
            if not phonetic_text:
                continue
            
            # 查找区域标识 - 在同一个容器中查找
            region_element = container.find('span', class_='region')
            if region_element:
                region_text = region_element.get_text(strip=True).lower()
                if 'uk' in region_text:
                    phonetics['uk'] = phonetic_text
                elif 'us' in region_text:
                    phonetics['us'] = phonetic_text
            else:
                # 如果没有区域标识，检查父级容器的class
                parent_classes = ' '.join(container.get('class', []))
                if 'uk' in parent_classes:
                    phonetics['uk'] = phonetic_text
                elif 'us' in parent_classes:
                    phonetics['us'] = phonetic_text
                else:
                    # 作为通用音标
                    if 'general' not in phonetics:
                        phonetics['general'] = phonetic_text
        
        return phonetics
    
    def _extract_audio_urls(self, soup: BeautifulSoup, word: str) -> Dict[str, str]:
        """提取音频URL"""
        audio_urls = {}
        
        # 查找所有source元素（mp3格式）
        source_elements = soup.find_all('source', {'type': 'audio/mpeg'})
        
        # 用于存储候选音频URL
        uk_candidates = []
        us_candidates = []
        
        for source in source_elements:
            src = source.get('src')
            if not src:
                continue
            
            # 构造完整URL
            if src.startswith('/'):
                full_url = self.config.cambridge_audio_base + src
            else:
                full_url = src
            
            # 通过URL路径判断是美式还是英式音频
            if '/uk_pron/' in src:
                uk_candidates.append(full_url)
            elif '/us_pron/' in src:
                us_candidates.append(full_url)
        
        # 选择最合适的音频文件
        # 优先选择文件名与单词匹配的音频
        def select_best_audio(candidates: List[str], word: str) -> Optional[str]:
            if not candidates:
                return None
            
            # 优先选择文件名包含单词的音频
            for url in candidates:
                filename = os.path.basename(url).lower()
                if word.lower() in filename:
                    return url
            
            # 如果没有匹配的，选择第一个（通常是主要发音）
            return candidates[0]
        
        if uk_candidates:
            audio_urls['uk'] = select_best_audio(uk_candidates, word)
        
        if us_candidates:
            audio_urls['us'] = select_best_audio(us_candidates, word)
        
        return audio_urls
    
    def download_audio(self, url: str, word: str, variant: str, audio_dir: str) -> Optional[str]:
        """
        下载音频文件到本地
        
        Args:
            url: 音频URL
            word: 单词
            variant: 变体 (uk/us)
            audio_dir: 音频目录
            
        Returns:
            本地音频文件路径，失败返回None
        """
        try:
            os.makedirs(audio_dir, exist_ok=True)
            
            # 生成本地文件名
            filename = f"{word}_{variant}.mp3"
            local_path = os.path.join(audio_dir, filename)
            
            # 如果文件已存在，直接返回
            if os.path.exists(local_path):
                return local_path
            
            # 下载音频文件
            response = self.session.get(url, timeout=self.config.timeout)
            if response.status_code == 200:
                with open(local_path, 'wb') as f:
                    f.write(response.content)
                print(f"    🔊 {word}({variant}): 音频下载成功")
                return local_path
            else:
                print(f"    ❌ {word}({variant}): 音频下载失败 ({response.status_code})")
                return None
                
        except Exception as e:
            print(f"    ❌ {word}({variant}): 音频下载异常 - {e}")
            return None


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
        
        # 初始化剑桥词典API
        self.cambridge_api = CambridgeDictionaryAPI(config)
        
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
    
    def enrich_vocabulary_with_cambridge(self, master_vocab_path: str) -> bool:
        """
        使用剑桥词典为词汇补充音标和音频信息
        
        Args:
            master_vocab_path: 总词汇表文件路径
            
        Returns:
            是否处理成功
        """
        print(f"🔄 步骤3: 使用剑桥词典补充音标和音频信息...")
        
        # 加载总词汇表
        master_vocab = self._load_master_vocabulary(master_vocab_path)
        if not master_vocab:
            print("⚠️ 没有词汇需要补充音标和音频")
            return True
        
        # 创建音频目录
        vocab_dir = os.path.dirname(master_vocab_path)
        audio_dir = os.path.join(vocab_dir, self.config.audio_download_dir)
        
        # 找出需要补充信息的词汇
        words_need_cambridge = []
        for word, info in master_vocab.items():
            # 检查是否已有剑桥词典信息
            if not info.get("phonetic_uk") and not info.get("phonetic_us"):
                words_need_cambridge.append(word)
        
        if not words_need_cambridge:
            print("✅ 所有词汇都已有剑桥词典信息")
            return True
        
        print(f"📝 发现 {len(words_need_cambridge)} 个词汇需要补充剑桥词典信息")
        
        # 处理每个单词
        enriched_count = 0
        for i, word in enumerate(words_need_cambridge, 1):
            print(f"  🔄 处理 {word} ({i}/{len(words_need_cambridge)})")
            
            # 获取剑桥词典信息
            cambridge_info = self.cambridge_api.get_word_info(word)
            if cambridge_info:
                # 更新音标信息
                phonetics = cambridge_info.get('phonetics', {})
                if phonetics.get('uk'):
                    master_vocab[word]["phonetic_uk"] = phonetics['uk']
                if phonetics.get('us'):
                    master_vocab[word]["phonetic_us"] = phonetics['us']
                if phonetics.get('general') and not master_vocab[word].get("phonetic"):
                    master_vocab[word]["phonetic"] = phonetics['general']
                
                # 下载音频并更新URL
                audio_urls = cambridge_info.get('audio_urls', {})
                if audio_urls.get('uk'):
                    local_path = self.cambridge_api.download_audio(
                        audio_urls['uk'], word, 'uk', audio_dir
                    )
                    if local_path:
                        master_vocab[word]["audio_url_uk"] = f"vocabulary/audio/{word}_uk.mp3"
                
                if audio_urls.get('us'):
                    local_path = self.cambridge_api.download_audio(
                        audio_urls['us'], word, 'us', audio_dir
                    )
                    if local_path:
                        master_vocab[word]["audio_url_us"] = f"vocabulary/audio/{word}_us.mp3"
                
                enriched_count += 1
                
            # 添加延迟避免请求过快
            time.sleep(0.5)
        
        # 保存更新的总词汇表
        self._save_master_vocabulary(master_vocab, master_vocab_path)
        
        print(f"✅ 剑桥词典信息补充完成: 成功处理 {enriched_count}/{len(words_need_cambridge)} 个词汇")
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
                    "phonetic_uk": "",  # 英式音标，从剑桥词典获取
                    "phonetic_us": "",  # 美式音标，从剑桥词典获取
                    "translation": translation,
                    "tags": tags,
                    "exchange": exchange,
                    "bnc": ecdict_info.get("bnc", 0),
                    "frq": ecdict_info.get("frq", 0),
                    "audio_url": "",  # 保留原字段兼容性
                    "audio_url_uk": "",  # 英式音频URL
                    "audio_url_us": "",  # 美式音频URL
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