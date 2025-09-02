#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
词汇管理器 - 统一管理单词提取和富化流程
"""

import os
import json
from typing import List, Dict, Tuple
from dataclasses import dataclass
from pathlib import Path

from .word_extractor import WordExtractor, WordExtractionConfig
from .vocabulary_enricher import VocabularyEnricher, VocabularyEnricherConfig, load_master_vocabulary

@dataclass
class VocabularyManagerConfig:
    """词汇管理器配置"""
    
    # 默认路径配置
    default_master_vocab_path: str = "vocabulary/master_vocabulary.json"
    
    # 子模块配置
    extraction: WordExtractionConfig = None
    enrichment: VocabularyEnricherConfig = None
    
    def __post_init__(self):
        """初始化默认值"""
        if self.extraction is None:
            self.extraction = WordExtractionConfig()
        if self.enrichment is None:
            self.enrichment = VocabularyEnricherConfig()


class VocabularyManager:
    """词汇管理器 - 统一处理单词提取、富化和存储"""
    
    def __init__(self, config: VocabularyManagerConfig):
        """
        初始化词汇管理器
        
        Args:
            config: 管理器配置
        """
        self.config = config
        
        # 初始化子模块
        self.extractor = WordExtractor(self.config.extraction)
        self.enricher = VocabularyEnricher(self.config.enrichment)
        
        print("📚 词汇管理器初始化完成")
    
    def process_book_vocabulary(self, sentence_files: List[str], output_dir: str, 
                              book_name: str, master_vocab_path: str = None) -> List[str]:
        """
        处理书籍词汇 - 完整流程（以子章节为单位）
        
        Args:
            sentence_files: 句子文件路径列表
            output_dir: 输出目录
            book_name: 书籍名称
            master_vocab_path: 总词汇表路径（可选）
            
        Returns:
            生成的子章节词汇文件列表
        """
        # 使用默认或指定的总词汇表路径
        print(f"📖 使用总词汇表: {master_vocab_path}")
        
        # 第一步：提取子章节词汇（提取所有单词）
        print(f"\n🔄 第1步: 从 {len(sentence_files)} 个句子文件中提取词汇...")
        subchapter_vocab_files, all_words = self.extractor.extract_subchapter_words(
            sentence_files, output_dir, master_vocab_path
        )
        
        # 加载现有总词汇表，判断哪些是新词
        existing_vocab = load_master_vocabulary(master_vocab_path)
        new_words = [word for word in all_words if word not in existing_vocab]
        
        if not new_words:
            print("✅ 所有词汇都已存在于总词汇表中，跳过富化步骤")
            return subchapter_vocab_files
        
        # 第二步：使用ECDICT补充基础信息
        print(f"\n🔄 第2步: 使用ECDICT为 {len(new_words)} 个新词汇补充基础信息...")
        success = self.enricher.enrich_vocabulary_with_ecdict(
            new_words, master_vocab_path
        )
        
        if not success:
            print(f"⚠️ ECDICT基础信息补充失败")
            return subchapter_vocab_files
        
        # 第三步：使用API补充音频信息
        print(f"\n🔄 第3步: 为词汇补充音频信息...")
        audio_success = self.enricher.enrich_vocabulary_with_cambridge(master_vocab_path)
        
        if audio_success:
            print(f"✅ 词汇处理完成!")
            print(f"📄 子章节词汇文件: {len(subchapter_vocab_files)} 个")
            print(f"📚 总词汇表: {master_vocab_path}")
        else:
            print(f"⚠️ 音频信息补充过程中出现错误，但基础信息已保存")
        
        return subchapter_vocab_files
    
    def get_vocabulary_stats(self, master_vocab_path: str) -> Dict:
        """获取词汇统计信息"""
        if not os.path.exists(master_vocab_path):
            return {}
        
        try:
            with open(master_vocab_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                metadata = data.get("metadata", {})
                # 确保返回的统计数据是最新的格式
                if 'level_distribution' in metadata:
                    # 如果是旧格式的level_distribution，转换为标签格式
                    level_dist = metadata['level_distribution']
                    if any(key.isdigit() or '级' in key or 'Level' in key for key in level_dist.keys()):
                        # 旧格式，返回空的标签分布
                        metadata['level_distribution'] = {}
                return metadata
        except Exception as e:
            print(f"⚠️ 获取词汇统计失败: {e}")
            return {}