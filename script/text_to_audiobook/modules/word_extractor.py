#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单词提取模块
从章节文本中提取单词，进行词形还原，过滤处理
"""

import os
import re
import json
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

# 需要安装: pip install spacy nltk
# 下载模型: python -m spacy download en_core_web_sm
try:
    import spacy
    import nltk
    from nltk.corpus import stopwords
    from nltk.corpus import names
except ImportError as e:
    print(f"❌ 缺少依赖包: {e}")
    print("请安装: pip install spacy nltk")
    print("并下载模型: python -m spacy download en_core_web_sm")
    raise


@dataclass
class WordExtractionConfig:
    """单词提取配置"""
    
    # 过滤配置
    min_word_length: int = 2
    max_word_length: int = 20
    filter_numbers: bool = True
    filter_proper_nouns: bool = True
    filter_stop_words: bool = True
    filter_names: bool = True
    
    # 输出配置
    vocabulary_subdir: str = "vocabulary"
    chapters_subdir: str = "chapters"
    
    # SpaCy模型
    spacy_model: str = "en_core_web_sm"


class WordExtractor:
    """单词提取器 - 从文本中提取和标准化单词"""
    
    def __init__(self, config: WordExtractionConfig):
        """
        初始化单词提取器
        
        Args:
            config: 提取配置
        """
        self.config = config
        
        # 加载SpaCy模型
        try:
            self.nlp = spacy.load(self.config.spacy_model)
            print(f"✅ SpaCy模型加载成功: {self.config.spacy_model}")
        except OSError:
            raise RuntimeError(f"SpaCy模型加载失败: {self.config.spacy_model}，请运行: python -m spacy download {self.config.spacy_model}")
        
        # 下载NLTK数据
        self._ensure_nltk_data()
        
        # 获取停用词和人名列表
        self.stop_words = set(stopwords.words('english'))
        self.names_list = set(names.words())
        
        print(f"📝 单词提取器初始化完成")
    
    def _ensure_nltk_data(self):
        """确保NLTK数据已下载"""
        try:
            nltk.data.find('corpora/stopwords')
            nltk.data.find('corpora/names')
        except LookupError:
            print("📥 下载NLTK数据...")
            nltk.download('stopwords', quiet=True)
            nltk.download('names', quiet=True)
    
    def extract_subchapter_words(self, sentence_files: List[str], output_dir: str, master_vocab_path: str) -> Tuple[List[str], List[str]]:
        """
        从句子文件中提取子章节词汇（以子章节为单位）
        
        Args:
            sentence_files: 句子文件路径列表
            output_dir: 输出目录
            master_vocab_path: 总词汇表文件路径
            
        Returns:
            (处理的子章节词汇文件列表, 所有新词列表)
        """
        # 加载已有的总词汇表
        existing_vocab = self._load_master_vocabulary(master_vocab_path)
        print(f"📝 加载现有词汇表: {len(existing_vocab)} 个单词")
        
        # 创建输出目录
        vocab_dir = os.path.join(output_dir, self.config.vocabulary_subdir)
        subchapters_dir = os.path.join(vocab_dir, "subchapters")
        os.makedirs(subchapters_dir, exist_ok=True)
        
        subchapter_vocab_files = []
        all_new_words = set()
        
        # 按子章节处理句子文件（每个句子文件对应一个子章节）
        for sentence_file in sentence_files:
            # 获取子章节名称
            filename = os.path.basename(sentence_file)
            subchapter_name = os.path.splitext(filename)[0]
            
            print(f"📝 处理子章节: {subchapter_name}")
            
            # 提取子章节所有单词
            all_words, filtered_words = self._extract_words_from_files([sentence_file])
            
            # 分离新词和已知词
            known_words = [word for word in all_words if word in existing_vocab]
            new_words = [word for word in all_words if word not in existing_vocab]
            
            # 收集所有新词
            all_new_words.update(new_words)
            
            # 保存子章节词汇文件（只包含单词文本）
            subchapter_vocab_data = {
                "subchapter_id": subchapter_name,
                "words": sorted(list(set(all_words))),  # 提取所有单词（包括新词和已知词）
                "word_count": len(set(all_words)),
                "filtered_words": sorted(list(set(filtered_words))),
                "new_words_count": len(new_words),
                "known_words_count": len(known_words)
            }
            
            subchapter_vocab_file = os.path.join(subchapters_dir, f"{subchapter_name}.json")
            self._save_json(subchapter_vocab_data, subchapter_vocab_file)
            subchapter_vocab_files.append(subchapter_vocab_file)
            
            print(f"  📄 已保存子章节词汇: {subchapter_vocab_file}")
            print(f"  📈 词汇统计: 总计{len(set(all_words))}个, 新词{len(new_words)}个, 已知{len(known_words)}个")
        
        print(f"\n📝 子章节词汇提取完成，发现 {len(all_new_words)} 个新词需要处理")
        return subchapter_vocab_files, list(all_new_words)
    
    def extract_chapter_words(self, sentence_files: List[str], output_dir: str, master_vocab_path: str) -> Tuple[List[str], List[str]]:
        """
        从句子文件中提取章节词汇（保留以兼容旧接口）
        
        Args:
            sentence_files: 句子文件路径列表
            output_dir: 输出目录
            master_vocab_path: 总词汇表文件路径
            
        Returns:
            (处理的章节词汇文件列表, 所有新词列表)
        """
        print("⚠️ 使用旧的章节级别接口，建议使用 extract_subchapter_words 方法")
        return self.extract_subchapter_words(sentence_files, output_dir, master_vocab_path)
    
    def _group_sentence_files_by_chapter(self, sentence_files: List[str]) -> Dict[str, List[str]]:
        """按章节名称分组句子文件"""
        chapter_groups = defaultdict(list)
        
        for sentence_file in sentence_files:
            # 从文件名提取章节名称 (例: 01_Down_the_Rabbit-Hole(1).txt -> 01_Down_the_Rabbit-Hole)
            filename = os.path.basename(sentence_file)
            base_name = os.path.splitext(filename)[0]
            
            # 移除括号部分，获取章节基础名称
            chapter_name = re.sub(r'\([^)]*\)$', '', base_name)
            chapter_groups[chapter_name].append(sentence_file)
        
        return dict(chapter_groups)
    
    def _extract_words_from_files(self, sentence_files: List[str]) -> Tuple[List[str], List[str]]:
        """
        从文件列表中提取单词
        
        Returns:
            (有效单词列表, 被过滤单词列表)
        """
        all_text = ""
        
        # 读取所有文件内容
        for sentence_file in sentence_files:
            try:
                with open(sentence_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 跳过第一行标题
                    lines = content.strip().split('\n')
                    if len(lines) > 1:
                        all_text += " " + " ".join(lines[1:])
            except Exception as e:
                print(f"⚠️ 读取文件失败: {sentence_file}, {e}")
                continue
        
        return self._extract_words_from_text(all_text)
    
    def _extract_words_from_text(self, text: str) -> Tuple[List[str], List[str]]:
        """
        从文本中提取单词并进行词形还原和过滤
        
        Returns:
            (有效单词列表, 被过滤单词列表)
        """
        if not text.strip():
            return [], []
        
        # 使用SpaCy处理文本
        doc = self.nlp(text)
        
        valid_words = []
        filtered_words = []
        
        for token in doc:
            original = token.text.lower().strip()
            
            # 基础过滤
            if not original or not original.isalpha():
                filtered_words.append(original)
                continue
            
            # 长度过滤
            if len(original) < self.config.min_word_length or len(original) > self.config.max_word_length:
                filtered_words.append(original)
                continue
            
            # 应用各种过滤规则
            filter_reason = self._get_filter_reason(token, original)
            if filter_reason:
                filtered_words.append(original)
                continue
            
            # 只对复数和第三人称单数进行归一化
            normalized_word = self._normalize_word_selective(token, original)
            valid_words.append(normalized_word)
        
        return valid_words, filtered_words
    
    def _get_filter_reason(self, token, word: str) -> Optional[str]:
        """
        检查单词是否应该被过滤
        
        Returns:
            过滤原因，如果不需要过滤返回None
        """
        # 停用词过滤
        if self.config.filter_stop_words and word in self.stop_words:
            return "stop_word"
        
        # 专有名词过滤
        if self.config.filter_proper_nouns and token.pos_ == "PROPN":
            return "proper_noun"
        
        # 人名过滤
        if self.config.filter_names and token.text in self.names_list:
            return "person_name"
        
        # 数字过滤
        if self.config.filter_numbers and token.like_num:
            return "number"
        
        return None
    
    def _normalize_word_selective(self, token, word: str) -> str:
        """
        选择性词形归一化：只归一化复数和第三人称单数形式
        
        Args:
            token: SpaCy token对象
            word: 原始单词
            
        Returns:
            归一化后的单词
        """
        lemma = token.lemma_.lower().strip()
        
        # 如果原词和词根相同，无需归一化
        if word == lemma:
            return word
        
        # 检查词性和变化类型
        pos = token.pos_
        tag = token.tag_
        
        # 名词复数归一化 (NNS -> NN)
        if pos == "NOUN" and tag == "NNS":
            return lemma
        
        # 动词第三人称单数归一化 (VBZ -> VB)
        if pos == "VERB" and tag == "VBZ":
            return lemma
        
        # 其他情况保持原形（包括动词时态VBD/VBG/VBN和形容词比较级JJR/JJS）
        return word
    
    def _load_master_vocabulary(self, master_vocab_path: str) -> Dict[str, Dict]:
        """加载总词汇表"""
        if not os.path.exists(master_vocab_path):
            print(f"📝 总词汇表不存在，将创建新文件: {master_vocab_path}")
            return {}
        
        try:
            with open(master_vocab_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('vocabulary', {})
        except Exception as e:
            print(f"⚠️ 加载总词汇表失败: {e}，使用空词汇表")
            return {}
    
    def _save_json(self, data: dict, file_path: str):
        """保存JSON数据到文件"""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)