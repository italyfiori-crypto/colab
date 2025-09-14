#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
流程执行模块 - 执行各个处理步骤的具体逻辑
"""

import os
import time
from typing import List, Tuple, Optional, Dict, Any
from .config import AudiobookConfig
from .chapter_splitter import ChapterSplitter
from .sub_chapter_splitter import SubChapterSplitter
from .sentence_splitter import SentenceSplitter
from .audio_generator import AudioGenerator, AudioGeneratorConfig
from .subtitle_parser import SubtitleParser
from .audio_compressor import AudioCompressor
from .vocabulary_manager import VocabularyManager, VocabularyManagerConfig
from .statistics_collector import StatisticsCollector
from .file_filter import filter_files_for_audio_generation, filter_files_for_subtitle_translation
from .path_utils import get_expected_audio_file, get_expected_subtitle_file


def execute_chapter_splitting(input_file: str, output_dir: str, config, verbose: bool = False) -> Tuple[List[str], float]:
    """
    执行章节拆分
    
    Returns:
        (章节文件列表, 耗时)
    """
    print(f"\n🔄 开始章节拆分处理...")
    start_time = time.time()
    
    splitter = ChapterSplitter(config)
    chapter_files = splitter.split_book(input_file, output_dir)
    elapsed_time = time.time() - start_time
    
    print(f"\n✅ 章节拆分完成! 共生成 {len(chapter_files)} 个章节文件 (耗时: {elapsed_time:.2f}秒)")
    
    return chapter_files, elapsed_time


def execute_sub_chapter_splitting(chapter_files: List[str], output_dir: str, config, verbose: bool = False) -> Tuple[List[str], float]:
    """
    执行子章节拆分
    
    Returns:
        (子章节文件列表, 耗时)
    """
    print(f"\n🔄 开始子章节拆分处理...")
    start_time = time.time()
    
    sub_splitter = SubChapterSplitter(config.sub_chapter)
    sub_chapter_files = sub_splitter.split_chapters(chapter_files, output_dir)
    elapsed_time = time.time() - start_time
    
    print(f"\n✅ 子章节拆分完成! 生成 {len(sub_chapter_files)} 个子章节文件 (耗时: {elapsed_time:.2f}秒)")
    
    return sub_chapter_files, elapsed_time


def execute_sentence_splitting(sub_chapter_files: List[str], output_dir: str, config, verbose: bool = False) -> Tuple[List[str], float]:
    """
    执行句子拆分
    
    Returns:
        (句子文件列表, 耗时)
    """
    print(f"\n🔄 开始句子拆分处理...")
    start_time = time.time()
    
    sentence_splitter = SentenceSplitter(config.sentence)
    sentence_files = sentence_splitter.split_files(sub_chapter_files, output_dir)
    elapsed_time = time.time() - start_time
    
    print(f"\n✅ 句子拆分完成! 最终生成 {len(sentence_files)} 个句子文件 (耗时: {elapsed_time:.2f}秒)")
    
    return sentence_files, elapsed_time


def execute_audio_generation(sentence_files: List[str], output_dir: str, voice: str, speed: float, verbose: bool = False) -> Tuple[List[str], List[str], float]:
    """
    执行音频生成
    
    Returns:
        (音频文件列表, 字幕文件列表, 耗时)
    """
    print(f"\n🔊 开始音频生成处理...")
    
    # 过滤需要生成音频的文件
    files_to_process, skipped_count = filter_files_for_audio_generation(sentence_files, output_dir)
    
    if skipped_count > 0:
        print(f"📋 跳过 {skipped_count} 个已存在的音频文件")
    
    audio_files = []
    subtitle_files = []
    elapsed_time = 0
    
    if files_to_process:
        print(f"🎵 需要生成 {len(files_to_process)} 个音频文件")
        start_time = time.time()
        try:
            audio_config = AudioGeneratorConfig(voice=voice, speed=speed)
            audio_generator = AudioGenerator(audio_config)
            audio_files, subtitle_files = audio_generator.generate_audio_files(files_to_process, output_dir)
            elapsed_time = time.time() - start_time
            
            total_audio_files = len(audio_files) + skipped_count
            total_subtitle_files = len(subtitle_files) + skipped_count
            print(f"\n✅ 音频生成完成! 总计 {total_audio_files} 个音频文件 (新生成 {len(audio_files)} 个) 和 {total_subtitle_files} 个字幕文件 (新生成 {len(subtitle_files)} 个) (耗时: {elapsed_time:.2f}秒)")
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"\n⚠️ 音频生成失败: {e} (耗时: {elapsed_time:.2f}秒)")
            if verbose:
                import traceback
                traceback.print_exc()
            print("继续执行其他步骤...")
    else:
        print(f"✅ 所有音频文件已存在，跳过音频生成步骤")
        # 收集所有音频和字幕文件（包括已存在的）
        for sentence_file in sentence_files:
            audio_file = get_expected_audio_file(sentence_file, output_dir)
            subtitle_file = get_expected_subtitle_file(sentence_file, output_dir)
            if os.path.exists(audio_file) and os.path.getsize(audio_file) > 0:
                audio_files.append(audio_file)
            if os.path.exists(subtitle_file):
                subtitle_files.append(subtitle_file)
    
    return audio_files, subtitle_files, elapsed_time


def execute_subtitle_parsing(subtitle_files: List[str], output_dir: str, config, verbose: bool = False) -> Tuple[List[str], float]:
    """
    执行字幕解析
    
    Returns:
        (解析文件列表, 耗时)
    """
    if not subtitle_files:
        print(f"\n⚠️ 未找到字幕文件，跳过解析步骤（请先启用 --audio 生成字幕）")
        return [], 0
    
    print(f"\n🔍 开始字幕解析处理...")
    
    files_to_parse = sorted(subtitle_files)
    parsed_files = []
    elapsed_time = 0
    
    if files_to_parse:
        print(f"🔍 需要解析 {len(files_to_parse)} 个字幕文件")
        start_time = time.time()
        try:
            # 配置解析器
            parser_config = config.subtitle_parser                
            if not parser_config.api_key:
                raise RuntimeError("缺少 SiliconFlow API 密钥，请通过 --api-key 参数或配置文件提供")
            
            parser = SubtitleParser(parser_config)
            parsed_files = parser.parse_subtitle_files(files_to_parse, output_dir)
            elapsed_time = time.time() - start_time
            
            total_parsed = len(parsed_files) + skipped_count
            print(f"\n✅ 字幕解析完成! 总计 {total_parsed} 个字幕文件包含中文翻译 (新解析 {len(parsed_files)} 个) (耗时: {elapsed_time:.2f}秒)")
        except Exception as e:
            elapsed_time = time.time() - start_time
            print(f"\n⚠️ 字幕解析失败: {e} (耗时: {elapsed_time:.2f}秒)")
            if verbose:
                import traceback
                traceback.print_exc()
            print("继续执行其他步骤...")
    else:
        print(f"✅ 所有字幕文件已包含中文翻译，跳过解析步骤")
        parsed_files = subtitle_files  # 所有文件都已解析
    
    return parsed_files, elapsed_time


def execute_audio_compression(audio_files: List[str], output_dir: str, config, verbose: bool = False) -> float:
    """
    执行音频压缩
    
    Returns:
        耗时
    """
    if not audio_files:
        print(f"\n⚠️ 未找到音频文件，跳过压缩步骤（请先启用 --audio 生成音频）")
        return 0
    
    print(f"\n🗜️ 开始音频压缩处理...")
    start_time = time.time()
    
    try:
        # 获取压缩配置
        compression_config = config.audio_compression
        compressor = AudioCompressor(compression_config.__dict__)
        
        # 压缩音频文件
        compression_results = compressor.compress_book_audio(output_dir, compression_config.output_subdir)
        elapsed_time = time.time() - start_time
        
        print(f"\n✅ 音频压缩完成! (耗时: {elapsed_time:.2f}秒)")
        
        if verbose and compression_results:
            print(f"📊 压缩统计:")
            for format_name, stats in compression_results.items():
                print(f"  {format_name.upper()}: {stats['files_success']}/{stats['files_processed']} 文件, 压缩比 {stats['compression_ratio']:.1f}%")
        
        return elapsed_time
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"\n⚠️ 音频压缩失败: {e} (耗时: {elapsed_time:.2f}秒)")
        if verbose:
            import traceback
            traceback.print_exc()
        print("继续执行其他步骤...")
        return elapsed_time


def execute_vocabulary_processing(sentence_files: List[str], output_dir: str, book_name: str, master_vocab_path: str, config, verbose: bool = False) -> Tuple[List[str], float]:
    """
    执行词汇处理
    
    Returns:
        (章节词汇文件列表, 耗时)
    """
    if not sentence_files:
        print(f"\n⚠️ 未找到句子文件，跳过词汇处理步骤")
        return [], 0
    
    print(f"\n📚 开始词汇提取和分级处理...")
    start_time = time.time()
    
    try:
        # 配置词汇管理器
        vocab_config = VocabularyManagerConfig()
        
        # 设置API密钥（如果需要）
        if config.subtitle_parser.api_key:
            vocab_config.enrichment.siliconflow_api_key = config.subtitle_parser.api_key
        
        vocab_manager = VocabularyManager(vocab_config)

        # 处理词汇
        chapter_vocab_files = vocab_manager.process_book_vocabulary(
            sentence_files=sentence_files,
            output_dir=output_dir,
            book_name=book_name,
            master_vocab_path=master_vocab_path
        )
        
        elapsed_time = time.time() - start_time
        print(f"\n✅ 词汇处理完成! 生成 {len(chapter_vocab_files)} 个章节词汇文件 (耗时: {elapsed_time:.2f}秒)")
        
        # 显示词汇统计
        if verbose:
            stats = vocab_manager.get_vocabulary_stats(master_vocab_path)
            if stats:
                print(f"📊 总词汇表统计:")
                print(f"  总词汇数: {stats.get('total_words', 0)}")
                if 'level_distribution' in stats:
                    for level_name, count in stats['level_distribution'].items():
                        print(f"  {level_name}: {count}词")
        
        return chapter_vocab_files, elapsed_time
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"\n⚠️ 词汇处理失败: {e} (耗时: {elapsed_time:.2f}秒)")
        if verbose:
            import traceback
            traceback.print_exc()
        print("继续执行其他步骤...")
        return [], elapsed_time


def execute_statistics_collection(sub_chapter_files: List[str], audio_files: List[str], output_dir: str, config, translate_enabled: bool = False, verbose: bool = False) -> Tuple[Optional[Dict[str, Any]], float]:
    """
    执行统计信息收集
    
    Returns:
        (统计信息字典, 耗时)
    """
    if not audio_files:
        print(f"\n⚠️ 未找到音频文件，跳过统计收集步骤（请先启用 --audio 生成音频）")
        return None, 0
    
    print(f"\n📊 开始统计信息收集...")
    start_time = time.time()
    
    try:
        statistics_collector = StatisticsCollector(config.statistics)
        
        # 收集统计信息（如果有翻译器就传入用于翻译章节标题）
        translator_for_stats = None
        if translate_enabled and config.subtitle_parser.api_key:
            translator_for_stats = SubtitleParser(config.subtitle_parser)
        
        statistics = statistics_collector.collect_statistics(
            sub_chapter_files=sub_chapter_files,
            audio_files=audio_files,
            output_dir=output_dir,
            translator=translator_for_stats
        )
        
        elapsed_time = time.time() - start_time
        print(f"\n✅ 统计信息收集完成! (耗时: {elapsed_time:.2f}秒)")
        
        if verbose and statistics:
            book_info = statistics.get('book', {})
            chapters_info = statistics.get('chapters', [])
            print(f"📖 书籍信息: {book_info.get('title', 'Unknown')} (共 {book_info.get('total_chapters', 0)} 章节, 总时长 {book_info.get('total_duration', 0):.1f}秒)")
            print(f"📊 收集了 {len(chapters_info)} 个章节的统计信息")
        
        return statistics, elapsed_time
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"\n⚠️ 统计信息收集失败: {e} (耗时: {elapsed_time:.2f}秒)")
        if verbose:
            import traceback
            traceback.print_exc()
        print("继续执行其他步骤...")
        return None, elapsed_time


def execute_vocabulary_audio_compression(audio_dir: str, compress_audio_dir: str, config: AudiobookConfig, verbose: bool = False) -> float:
    """
    执行单词音频压缩
    
    Returns:
        耗时
    """
    if not os.path.exists(audio_dir):
        if verbose:
            print(f"\n⚠️ 未找到单词音频目录，跳过单词音频压缩步骤")
        return 0
    
    print(f"\n🗜️ 开始单词音频压缩处理...")
    start_time = time.time()
    
    try:
        # 获取压缩配置
        compression_config = config.audio_compression
        compressor = AudioCompressor(compression_config.__dict__)
        
        # 压缩单词音频文件
        compression_results = compressor.compress_vocabulary_audio(audio_dir, compress_audio_dir)
        elapsed_time = time.time() - start_time
        
        print(f"\n✅ 单词音频压缩完成! (耗时: {elapsed_time:.2f}秒)")
        
        if verbose and compression_results:
            print(f"📊 单词音频压缩统计:")
            for format_name, stats in compression_results.items():
                print(f"  {format_name.upper()}: {stats['files_success']}/{stats['files_processed']} 文件, 压缩比 {stats['compression_ratio']:.1f}%")
        
        return elapsed_time
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"\n⚠️ 单词音频压缩失败: {e} (耗时: {elapsed_time:.2f}秒)")
        if verbose:
            import traceback
            traceback.print_exc()
        print("继续执行其他步骤...")
        return elapsed_time