#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流执行器 - 简化的流程编排
统一执行各个处理步骤
"""

import os
import time
from typing import List, Tuple, Optional, Dict, Any
from infra.config_loader import AppConfig
from util import OUTPUT_DIRECTORIES
from .text_processor import TextProcessor
from .audio_processor import AudioProcessor
from .translation_service import TranslationService
from .analysis_service import AnalysisService
from .statistics_service import StatisticsService
from .vocabulary_service import VocabularyService


class WorkflowExecutor:
    """简化的工作流执行器"""
    
    def __init__(self, config: AppConfig):
        """
        初始化工作流执行器
        
        Args:
            config: 应用配置
        """
        self.config = config
        self.text_processor = TextProcessor(config)
        self.audio_processor = AudioProcessor(config)
        self.translation_service = TranslationService(config)
        self.analysis_service = AnalysisService(config)
        self.statistics_service = StatisticsService(config)
        self.vocabulary_service = VocabularyService(config)
    
    def execute_text_processing(self, input_file: str, output_dir: str, verbose: bool = False) -> Tuple[List[str], List[str], List[str], float]:
        """
        执行完整的文本处理流程：章节拆分 + 子章节拆分 + 句子拆分
        
        Args:
            input_file: 输入文件
            output_dir: 输出目录
            verbose: 是否详细输出
            
        Returns:
            (章节文件列表, 子章节文件列表, 句子文件列表, 耗时)
        """
        print(f"\n🔄 开始文本处理流程...")
        start_time = time.time()
        
        try:
            chapter_files, sub_chapter_files, sentence_files = self.text_processor.split_book_to_sentences(input_file, output_dir)
            elapsed_time = time.time() - start_time
            
            print(f"\n✅ 文本处理完成! 生成:")
            print(f"  📖 章节文件: {len(chapter_files)} 个")
            print(f"  📑 子章节文件: {len(sub_chapter_files)} 个") 
            print(f"  📝 句子文件: {len(sentence_files)} 个")
            print(f"  ⏱️ 耗时: {elapsed_time:.2f}秒")
            
            return chapter_files, sub_chapter_files, sentence_files, elapsed_time
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"\n❌ 文本处理失败: {e} (耗时: {elapsed_time:.2f}秒)")
            if verbose:
                import traceback
                traceback.print_exc()
            return [], [], [], elapsed_time
    
    def execute_audio_processing(self, sentence_files: List[str], output_dir: str, voice: str = "af_bella", speed: float = 1.0, compress: bool = True, verbose: bool = False) -> Tuple[List[str], List[str], float]:
        """
        执行音频处理流程：音频生成 + 压缩
        
        Args:
            sentence_files: 句子文件列表
            output_dir: 输出目录
            voice: 声音类型
            speed: 语速
            compress: 是否压缩
            verbose: 是否详细输出
            
        Returns:
            (音频文件列表, 字幕文件列表, 耗时)
        """
        if not sentence_files:
            print("⚠️ 未找到句子文件，跳过音频处理")
            return [], [], 0
        
        print(f"\n🔊 开始音频处理流程...")
        start_time = time.time()
        
        try:
            audio_files, subtitle_files = self.audio_processor.process_audio_pipeline(
                sentence_files, output_dir, voice, speed, compress
            )
            elapsed_time = time.time() - start_time
            
            print(f"\n✅ 音频处理完成!")
            print(f"  🎵 音频文件: {len(audio_files)} 个")
            print(f"  📄 字幕文件: {len(subtitle_files)} 个")
            print(f"  ⏱️ 耗时: {elapsed_time:.2f}秒")
            
            return audio_files, subtitle_files, elapsed_time
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"\n❌ 音频处理失败: {e} (耗时: {elapsed_time:.2f}秒)")
            if verbose:
                import traceback
                traceback.print_exc()
            return [], [], elapsed_time
    
    def execute_translation_and_analysis(self, subtitle_files: List[str], sub_chapter_files: List[str], audio_files: List[str], output_dir: str, verbose: bool = False) -> Tuple[List[str], float]:
        """
        执行翻译和分析流程：字幕翻译 + 语言学分析
        
        Args:
            subtitle_files: 字幕文件列表
            sub_chapter_files: 子章节文件列表（未使用，保持接口兼容）
            audio_files: 音频文件列表（未使用，保持接口兼容）
            output_dir: 输出目录
            verbose: 是否详细输出
            
        Returns:
            (分析文件列表, 耗时)
        """
        if not subtitle_files:
            print("⚠️ 未找到字幕文件，跳过翻译和分析")
            return [], 0
        
        print(f"\n🔍 开始翻译和分析流程...")
        start_time = time.time()
        
        try:
            # 1. 翻译字幕
            translated_files = self.translation_service.translate_subtitle_files(subtitle_files)
            
            # 2. 语言学分析
            analyzed_files = self.analysis_service.analyze_subtitle_files(translated_files, output_dir)
            
            elapsed_time = time.time() - start_time
            
            print(f"\n✅ 翻译和分析完成!")
            print(f"  🌏 翻译文件: {len(translated_files)} 个")
            print(f"  🔍 分析文件: {len(analyzed_files)} 个")
            print(f"  ⏱️ 耗时: {elapsed_time:.2f}秒")
            
            return analyzed_files, elapsed_time
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"\n❌ 翻译和分析失败: {e} (耗时: {elapsed_time:.2f}秒)")
            if verbose:
                import traceback
                traceback.print_exc()
            return [], elapsed_time
    
    def execute_vocabulary_processing(self, sentence_files: List[str], output_dir: str, book_name: str, master_vocab_path: str, verbose: bool = False) -> Tuple[List[str], float]:
        """
        执行词汇处理流程
        
        Args:
            sentence_files: 句子文件列表
            output_dir: 输出目录
            book_name: 书籍名称
            master_vocab_path: 主词汇表路径
            verbose: 是否详细输出
            
        Returns:
            (词汇文件列表, 耗时)
        """
        if not sentence_files:
            print("⚠️ 未找到句子文件，跳过词汇处理")
            return [], 0
        
        print(f"\n📚 开始词汇处理流程...")
        start_time = time.time()
        
        try:
            chapter_vocab_files, success = self.vocabulary_service.process_vocabulary(
                sentence_files, output_dir, book_name, master_vocab_path
            )
            elapsed_time = time.time() - start_time
            
            if success:
                print(f"\n✅ 词汇处理完成!")
                print(f"  📚 词汇文件: {len(chapter_vocab_files)} 个")
                print(f"  ⏱️ 耗时: {elapsed_time:.2f}秒")
            else:
                print(f"\n❌ 词汇处理失败 (耗时: {elapsed_time:.2f}秒)")
            
            return chapter_vocab_files, elapsed_time
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"\n❌ 词汇处理失败: {e} (耗时: {elapsed_time:.2f}秒)")
            if verbose:
                import traceback
                traceback.print_exc()
            return [], elapsed_time
    
    # 保持向后兼容的单独函数
    def execute_chapter_splitting(self, input_file: str, output_dir: str, config, verbose: bool = False) -> Tuple[List[str], float]:
        """向后兼容：章节拆分"""
        chapter_files, _, _, elapsed_time = self.execute_text_processing(input_file, output_dir, verbose)
        return chapter_files, elapsed_time
    
    def execute_sub_chapter_splitting(self, chapter_files: List[str], output_dir: str, config, verbose: bool = False) -> Tuple[List[str], float]:
        """向后兼容：子章节拆分（实际上在text_processing中已完成）"""
        # 获取已存在的子章节文件
        sub_chapters_dir = os.path.join(output_dir, OUTPUT_DIRECTORIES['sub_chapters'])
        from infra.file_manager import FileManager
        file_manager = FileManager()
        sub_chapter_files = file_manager.get_files_by_extension(sub_chapters_dir, ".txt")
        return sub_chapter_files, 0
    
    def execute_sentence_splitting(self, sub_chapter_files: List[str], output_dir: str, config, verbose: bool = False) -> Tuple[List[str], float]:
        """向后兼容：句子拆分（实际上在text_processing中已完成）"""
        # 获取已存在的句子文件
        sentences_dir = os.path.join(output_dir, OUTPUT_DIRECTORIES['sentences'])
        from infra.file_manager import FileManager
        file_manager = FileManager()
        sentence_files = file_manager.get_files_by_extension(sentences_dir, ".txt")
        return sentence_files, 0
    
    def execute_audio_generation(self, sentence_files: List[str], output_dir: str, voice: str, speed: float, verbose: bool = False) -> Tuple[List[str], List[str], float]:
        """向后兼容：音频生成"""
        return self.execute_audio_processing(sentence_files, output_dir, voice, speed, False, verbose)
    
    def execute_subtitle_parsing(self, subtitle_files: List[str], output_dir: str, config, verbose: bool = False) -> Tuple[List[str], float]:
        """向后兼容：字幕解析"""
        analyzed_files, _, elapsed_time = self.execute_translation_and_analysis(subtitle_files, [], [], output_dir, verbose)
        return analyzed_files, elapsed_time
    
    def execute_audio_compression(self, audio_files: List[str], output_dir: str, config, verbose: bool = False) -> float:
        """向后兼容：音频压缩"""
        start_time = time.time()
        self.audio_processor.compress_audio_files(audio_files, output_dir)
        return time.time() - start_time
    
    def execute_statistics_collection(self, sub_chapter_files: List[str], audio_files: List[str], output_dir: str, verbose: bool = False) -> Tuple[Optional[Dict[str, Any]], float]:
        """独立的统计收集"""
        start_time = time.time()
        statistics = self.statistics_service.collect_statistics(sub_chapter_files, audio_files, output_dir)
        elapsed_time = time.time() - start_time
        return statistics, elapsed_time