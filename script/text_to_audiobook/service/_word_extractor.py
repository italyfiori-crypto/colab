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
from ._vocabulary_enricher import load_master_vocabulary

# 需要安装: pip install spacy
# 下载模型: python -m spacy download en_core_web_sm
try:
    import spacy
except ImportError as e:
    print(f"❌ 缺少依赖包: {e}")
    print("请安装: pip install spacy")
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
        
        # 获取spaCy停用词
        self.stop_words = self.nlp.Defaults.stop_words
        
        print(f"📝 单词提取器初始化完成")
    
    
    def extract_subchapter_words(self, sub_chapter_files: List[str], output_dir: str, master_vocab_path: str) -> Tuple[List[str], List[str]]:
        """
        从句子文件中提取子章节词汇（以子章节为单位）
        
        Args:
            sub_chapter_files: 句子文件路径列表
            output_dir: 输出目录
            master_vocab_path: 总词汇表文件路径
            
        Returns:
            (处理的子章节词汇文件列表, 所有新词列表)
        """
        # 加载已有的总词汇表
        existing_vocab = load_master_vocabulary(master_vocab_path)
        print(f"📝 加载现有词汇表: {len(existing_vocab)} 个单词")
        
        # 创建输出目录
        vocab_dir = os.path.join(output_dir, self.config.vocabulary_subdir)
        os.makedirs(vocab_dir, exist_ok=True)
        
        subchapter_vocab_files = []
        all_new_words = set()
        
        # 按子章节处理句子文件（每个句子文件对应一个子章节）
        for sub_chapter_file in sorted(sub_chapter_files):
            # 获取子章节名称
            filename = os.path.basename(sub_chapter_file)
            subchapter_name = os.path.splitext(filename)[0]
            
            print(f"📝 处理子章节: {subchapter_name}")
            
            # 提取子章节所有单词
            all_words, filtered_words = self._extract_words_from_files([sub_chapter_file])
            
            # 收集所有提取的单词（不区分新旧）
            all_new_words.update(all_words)
            
            # 第一阶段：保存原始单词列表（不格式化），保持原文顺序
            unique_words = self._preserve_order_dedup(all_words)  # 保序去重
            
            # 保存子章节词汇文件（第一阶段：只含单词列表）
            subchapter_vocab_data = {
                "word_list": unique_words,  # 第一阶段：纯单词列表，保持原文顺序
                "filtered_words": sorted(list(set(filtered_words)))
            }
            
            subchapter_vocab_file = os.path.join(vocab_dir, f"{subchapter_name}.json")
            self._save_json(subchapter_vocab_data, subchapter_vocab_file)
            subchapter_vocab_files.append(subchapter_vocab_file)
            
            print(f"  📄 已保存子章节词汇: {subchapter_name}")
            print(f"  📈 词汇统计: 总计{len(set(all_words))}个")
        
        print(f"\n📝 子章节词汇提取完成，共提取 {len(all_new_words)} 个单词")
        return subchapter_vocab_files, list(all_new_words)
    
    def _extract_words_from_files(self, sub_chapter_files: List[str]) -> Tuple[List[str], List[str]]:
        """
        从文件列表中提取单词
        
        Returns:
            (有效单词列表, 被过滤单词列表)
        """
        all_text = ""
        
        # 读取所有文件内容
        for sub_chapter_file in sub_chapter_files:
            try:
                with open(sub_chapter_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 跳过第一行标题
                    lines = content.strip().split('\n')
                    if len(lines) > 1:
                        all_text += " " + " ".join(lines[1:])
            except Exception as e:
                print(f"⚠️ 读取文件失败: {sub_chapter_file}, {e}")
                continue
        
        return self._extract_words_from_text(all_text)
    
    def _preserve_order_dedup(self, items: List[str]) -> List[str]:
        """
        保序去重函数 - 保持元素首次出现的顺序
        
        Args:
            items: 原始列表
            
        Returns:
            去重后保持原始顺序的列表
        """
        seen = set()
        result = []
        for item in items:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result
    
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
            
            valid_words.append(original)
        
        return valid_words, filtered_words
    
    def _format_words_with_info(self, words: List[str], vocab_dict: Dict[str, Dict]) -> List[str]:
        """
        将单词列表格式化为包含词汇信息的逗号分隔格式
        
        Args:
            words: 单词列表
            vocab_dict: 总词汇表字典
            
        Returns:
            格式化后的单词信息列表，格式为: word,tags,frq,collins,oxford
        """
        formatted_words = []
        unique_words = self._preserve_order_dedup(words)  # 保序去重
        
        for word in unique_words:
            word_info = vocab_dict.get(word, {})
            
            # 提取词汇信息，如果不存在则使用默认值
            tags = ""
            if 'tags' in word_info:
                if isinstance(word_info['tags'], list):
                    tags = " ".join(word_info['tags'])
                elif isinstance(word_info['tags'], str):
                    tags = word_info['tags']
            
            frq = word_info.get('frq', 0)
            collins = word_info.get('collins', 0)
            oxford = word_info.get('oxford', 0)
            
            # 格式化为逗号分隔字符串: word,tags,frq,collins,oxford
            formatted_word = f"{word},{tags},{frq},{collins},{oxford}"
            formatted_words.append(formatted_word)
        
        # 保持原文中出现的顺序，不进行排序
        return formatted_words
    
    def update_vocabulary_info(self, output_dir: str, master_vocab_path: str) -> bool:
        """
        第二阶段：更新章节词汇文件，将单词列表转换为逗号分隔信息格式
        
        Args:
            output_dir: 输出目录（包含vocabulary子目录）
            master_vocab_path: 总词汇表文件路径
            
        Returns:
            是否更新成功
        """
        try:
            # 加载总词汇表
            existing_vocab = load_master_vocabulary(master_vocab_path)
            if not existing_vocab:
                print("⚠️ 总词汇表为空，无法更新词汇信息")
                return False
            
            # 查找所有章节词汇文件
            vocab_dir = os.path.join(output_dir, self.config.vocabulary_subdir)
            if not os.path.exists(vocab_dir):
                print("⚠️ 章节词汇目录不存在")
                return False
            
            vocab_files = []
            for file in os.listdir(vocab_dir):
                if file.endswith('.json'):
                    vocab_files.append(os.path.join(vocab_dir, file))
            
            if not vocab_files:
                print("⚠️ 没有找到章节词汇文件")
                return False
            
            updated_count = 0
            
            print(f"📝 开始更新 {len(vocab_files)} 个章节词汇文件...")
            
            # 处理每个章节词汇文件
            for vocab_file in vocab_files:
                if self._update_single_vocab_file(vocab_file, existing_vocab):
                    updated_count += 1
                    filename = os.path.basename(vocab_file)
                    print(f"  ✅ 已更新: {filename}")
            
            print(f"\n📝 词汇信息更新完成: 成功更新 {updated_count}/{len(vocab_files)} 个文件")
            return updated_count > 0
            
        except Exception as e:
            print(f"❌ 更新词汇信息失败: {e}")
            return False
    
    def _update_single_vocab_file(self, vocab_file: str, vocab_dict: Dict[str, Dict]) -> bool:
        """
        更新单个章节词汇文件
        
        Args:
            vocab_file: 章节词汇文件路径
            vocab_dict: 总词汇表字典
            
        Returns:
            是否更新成功
        """
        try:
            # 读取现有文件
            with open(vocab_file, 'r', encoding='utf-8') as f:
                vocab_data = json.load(f)
            
            words = vocab_data.get('word_list', [])
            if not words:
                return False
            
            # 检查是否已经是格式化格式
            if isinstance(words[0], str) and ',' in words[0] and len(words[0].split(',')) == 5:
                print(f"  ⭕ 已是格式化格式，跳过: {os.path.basename(vocab_file)}")
                return False
            
            # 格式化单词信息
            formatted_words = self._format_words_with_info(words, vocab_dict)
            
            # 更新数据
            vocab_data['word_info_list'] = formatted_words
            
            # 保存更新后的文件
            self._save_json(vocab_data, vocab_file)
            return True
            
        except Exception as e:
            print(f"❌ 更新文件失败 {vocab_file}: {e}")
            return False
    
    def _save_json(self, data: dict, file_path: str):
        """保存JSON数据到文件"""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)