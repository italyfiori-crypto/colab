#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
词汇服务 - 统一的词汇处理功能
完全基于modules目录逻辑实现，整合词汇提取、管理和富化功能
"""

import os
import json
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from infra import FileManager
from infra.config_loader import AppConfig
from util import OUTPUT_DIRECTORIES

# 导入内部模块
from ._word_extractor import WordExtractor, WordExtractionConfig
from ._vocabulary_enricher import VocabularyEnricher, VocabularyEnricherConfig


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


class VocabularyService:
    """统一的词汇服务 - 完全基于modules/vocabulary_manager.py实现"""
    
    def __init__(self, config: AppConfig):
        """
        初始化词汇服务
        
        Args:
            config: 应用配置
        """
        self.config = config
        self.file_manager = FileManager()
        
        # 初始化配置（按modules/vocabulary_manager.py的逻辑）
        self.vocab_config = VocabularyManagerConfig()
        
        # 初始化子模块
        self.extractor = WordExtractor(self.vocab_config.extraction)
        self.enricher = VocabularyEnricher(self.vocab_config.enrichment)
        
        print("📚 词汇服务初始化完成")
    
    def process_vocabulary(self, sentence_files: List[str], output_dir: str, book_name: str, master_vocab_path: str) -> Tuple[List[str], bool]:
        """
        处理词汇提取和分级 - 完全按照modules/vocabulary_manager.py的process_book_vocabulary逻辑
        
        Args:
            sentence_files: 句子文件列表
            output_dir: 输出目录
            book_name: 书籍名称
            master_vocab_path: 主词汇表路径
            
        Returns:
            (章节词汇文件列表, 是否成功)
        """
        if not sentence_files:
            print("⚠️ 未找到句子文件，跳过词汇处理")
            return [], True
        
        try:
            # 使用默认或指定的总词汇表路径
            print(f"📖 使用总词汇表: {master_vocab_path}")
            
            # 第一步：提取子章节词汇（提取所有单词）
            print(f"\n🔄 第1步: 从 {len(sentence_files)} 个句子文件中提取词汇...")
            subchapter_vocab_files, all_words = self.extractor.extract_subchapter_words(
                sentence_files, output_dir, master_vocab_path
            )
                    
            if not all_words:
                print("✅ 没有新词汇需要处理")
                return subchapter_vocab_files, True
            
            # 第二步：使用ECDICT补充基础信息
            print(f"\n🔄 第2步: 使用ECDICT为 {len(all_words)} 个新词汇补充基础信息...")
            success = self.enricher.enrich_vocabulary_with_ecdict(all_words, master_vocab_path)
            
            if not success:
                print(f"⚠️ ECDICT基础信息补充失败")
                return subchapter_vocab_files, False
            
            # 第三步：使用API补充音频信息
            print(f"\n🔄 第3步: 为词汇补充音频信息...")
            audio_success = self.enricher.enrich_vocabulary_with_cambridge(master_vocab_path)
            
            if not audio_success:
                print(f"⚠️ 音频信息补充过程中出现错误，但基础信息已保存")
            
            # 第四步：更新章节词汇文件为详细格式（保持原文顺序）
            print(f"\n🔄 第4步: 更新章节词汇文件为详细格式...")
            update_success = self.extractor.update_vocabulary_info(output_dir, master_vocab_path)
            
            if update_success:
                print(f"✅ 词汇处理完成!")
                print(f"📄 子章节词汇文件: {len(subchapter_vocab_files)} 个")
                print(f"📚 总词汇表: {master_vocab_path}")
            else:
                print(f"⚠️ 章节词汇文件格式更新失败")
            
            return subchapter_vocab_files, True
            
        except Exception as e:
            print(f"❌ 词汇处理失败: {e}")
            return [], False
    
    def get_existing_vocabulary_files(self, output_dir: str) -> List[str]:
        """
        获取已存在的词汇文件
        
        Args:
            output_dir: 输出目录
            
        Returns:
            词汇文件列表
        """
        vocab_dir = os.path.join(output_dir, OUTPUT_DIRECTORIES['vocabulary'])
        return self.file_manager.get_files_by_extension(vocab_dir, ".json")
    
    def get_vocabulary_stats(self, master_vocab_path: str) -> Dict:
        """获取词汇统计信息 - 完全按照modules/vocabulary_manager.py的逻辑"""
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