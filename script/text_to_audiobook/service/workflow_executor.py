#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工作流执行器 - 简化的流程编排
统一执行各个处理步骤
"""

import os
import time
from typing import List, Tuple, Dict, Any
from infra.config_loader import AppConfig
from .chapter_processor import ChapterProcessor
from .sentence_processor import SentenceProcessor
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
        self.chapter_processor = ChapterProcessor(config)
        self.sentence_processor = SentenceProcessor(config)
        self.audio_processor = AudioProcessor(config)
        self.translation_service = TranslationService(config)
        self.analysis_service = AnalysisService(config)
        self.statistics_service = StatisticsService(config)
        self.vocabulary_service = VocabularyService(config)
    
    def execute_chapter_processing(self, input_file: str, output_dir: str, verbose: bool = False) -> Tuple[List[str], List[str], float]:
        """
        执行章节处理流程：章节拆分 + 子章节拆分
        
        Args:
            input_file: 输入文件
            output_dir: 输出目录
            verbose: 是否详细输出
            
        Returns:
            (章节文件列表, 子章节文件列表, 耗时)
        """
        start_time = time.time()
        
        try:
            chapter_files, sub_chapter_files = self.chapter_processor.split_book_to_sub_chapters(input_file, output_dir)
            elapsed_time = time.time() - start_time
            
            return chapter_files, sub_chapter_files, elapsed_time
            
        except Exception as e:
            print(f"❌ 章节拆分失败: {e}")
            raise
    
    def execute_sentence_processing(self, sub_chapter_files: List[str], output_dir: str, verbose: bool = False) -> Tuple[List[str], float]:
        """
        执行句子处理流程：句子拆分
        
        Args:
            sub_chapter_files: 子章节文件列表
            output_dir: 输出目录
            verbose: 是否详细输出
            force_regenerate: 是否强制重新生成
            
        Returns:
            (句子文件列表, 耗时)
        """
        start_time = time.time()
        
        try:
            sentence_files = self.sentence_processor.split_sub_chapters_to_sentences(sub_chapter_files, output_dir)
            elapsed_time = time.time() - start_time
            
            return sentence_files, elapsed_time
            
        except Exception as e:
            print(f"❌ 句子拆分失败: {e}")
            raise
    
    def execute_audio_processing(self, sentence_files: List[str], output_dir: str, voice: str, speed: float, verbose: bool = False) -> Tuple[List[str], List[str], float]:
        """
        执行音频处理流程
        
        Args:
            sentence_files: 句子文件列表
            output_dir: 输出目录
            voice: 语音模型
            speed: 语音速度
            verbose: 是否详细输出
            
        Returns:
            (音频文件列表, 字幕文件列表, 耗时)
        """
        print(f"\n🔄 开始音频生成流程...")
        start_time = time.time()
        
        try:
            audio_files, subtitle_files = self.audio_processor.generate_audio_files(
                sentence_files, output_dir, voice, speed
            )
            elapsed_time = time.time() - start_time
            
            print(f"\n✅ 音频生成完成! 生成:")
            print(f"  🎵 音频文件: {len(audio_files)} 个")
            print(f"  📄 字幕文件: {len(subtitle_files)} 个")
            print(f"  ⏱️ 耗时: {elapsed_time:.2f}秒")
            
            return audio_files, subtitle_files, elapsed_time
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"\n❌ 音频生成失败: {e} (耗时: {elapsed_time:.2f}秒)")
            if verbose:
                import traceback
                traceback.print_exc()
            raise
    
    def execute_audio_compression(self, audio_files: List[str], output_dir: str, verbose: bool = False) -> Tuple[List[str], float]:
        """
        执行音频压缩流程
        
        Args:
            audio_files: 音频文件列表
            output_dir: 输出目录
            verbose: 是否详细输出
            
        Returns:
            (压缩文件列表, 耗时)
        """
        print(f"\n🔄 开始音频压缩流程...")
        start_time = time.time()
        
        try:
            success = self.audio_processor.compress_audio_files(audio_files, output_dir)
            elapsed_time = time.time() - start_time
            
            if success:
                # 获取压缩后的文件列表
                from util.file_utils import get_existing_files
                from util import OUTPUT_DIRECTORIES
                compressed_files = get_existing_files(output_dir, OUTPUT_DIRECTORIES['compressed_audio'], ".mp3")
                
                print(f"\n✅ 音频压缩完成! 生成:")
                print(f"  🗜️ 压缩文件: {len(compressed_files)} 个")
                print(f"  ⏱️ 耗时: {elapsed_time:.2f}秒")
                
                return compressed_files, elapsed_time
            else:
                print(f"\n❌ 音频压缩失败 (耗时: {elapsed_time:.2f}秒)")
                return [], elapsed_time
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"\n❌ 音频压缩失败: {e} (耗时: {elapsed_time:.2f}秒)")
            if verbose:
                import traceback
                traceback.print_exc()
            raise
    
    def execute_analysis(self, subtitle_files: List[str], output_dir: str, verbose: bool = False) -> Tuple[List[str], float]:
        """
        执行分析流程
        
        Args:
            subtitle_files: 字幕文件列表
            output_dir: 输出目录
            verbose: 是否详细输出
            
        Returns:
            (分析文件列表, 耗时)
        """
        print(f"\n🔄 开始语言学分析流程...")
        start_time = time.time()
        
        try:
            # 处理分析
            analyzed_files = self.analysis_service.analyze_subtitle_files(subtitle_files, output_dir)
            
            elapsed_time = time.time() - start_time
            
            print(f"\n✅ 语言学分析完成! 分析:")
            print(f"  📊 分析文件: {len(analyzed_files)} 个")
            print(f"  ⏱️ 耗时: {elapsed_time:.2f}秒")
            
            return analyzed_files, elapsed_time
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"\n❌ 语言学分析失败: {e} (耗时: {elapsed_time:.2f}秒)")
            if verbose:
                import traceback
                traceback.print_exc()
            raise
    
    def execute_vocabulary_processing(self, sub_chapter_files: List[str], output_dir: str, book_name: str, master_vocab_file: str, verbose: bool = False) -> Tuple[List[str], float]:
        """
        执行词汇处理流程
        
        Args:
            sentence_files: 句子文件列表
            output_dir: 输出目录
            book_name: 书籍名称
            master_vocab_file: 总词汇表文件
            verbose: 是否详细输出
            
        Returns:
            (章节词汇文件列表, 耗时)
        """
        print(f"\n🔄 开始词汇处理流程...")
        start_time = time.time()
        
        try:
            chapter_vocab_files = self.vocabulary_service.process_vocabulary(
                sub_chapter_files, output_dir, book_name, master_vocab_file
            )
            elapsed_time = time.time() - start_time
            
            print(f"\n✅ 词汇处理完成! 生成:")
            print(f"  📚 章节词汇文件: {len(chapter_vocab_files)} 个")
            print(f"  ⏱️ 耗时: {elapsed_time:.2f}秒")
            
            return chapter_vocab_files, elapsed_time
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"\n❌ 词汇处理失败: {e} (耗时: {elapsed_time:.2f}秒)")
            if verbose:
                import traceback
                traceback.print_exc()
            raise
    
    def execute_statistics_collection(self, sub_chapter_files: List[str], audio_files: List[str], output_dir: str, verbose: bool = False) -> Tuple[Dict[str, Any], float]:
        """
        执行统计信息收集流程
        
        Args:
            sub_chapter_files: 子章节文件列表
            audio_files: 音频文件列表
            output_dir: 输出目录
            verbose: 是否详细输出
            
        Returns:
            (统计信息字典, 耗时)
        """
        print(f"\n🔄 开始统计信息收集...")
        start_time = time.time()
        
        try:
            statistics = self.statistics_service.collect_statistics(
                sub_chapter_files, audio_files, output_dir
            )
            elapsed_time = time.time() - start_time
            
            print(f"\n✅ 统计信息收集完成!")
            print(f"  📊 统计数据已保存到: {os.path.join(output_dir, 'meta.json')}")
            print(f"  ⏱️ 耗时: {elapsed_time:.2f}秒")
            
            return statistics, elapsed_time
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"\n❌ 统计信息收集失败: {e} (耗时: {elapsed_time:.2f}秒)")
            if verbose:
                import traceback
                traceback.print_exc()
            raise