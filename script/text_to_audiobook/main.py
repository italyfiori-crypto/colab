#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
章节拆分主程序 - 精简版
支持配置文件和最少的命令行参数
"""

import argparse
import sys
import os
import time
import re
from pathlib import Path

# 添加模块路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.chapter_splitter import ChapterSplitter
from modules.config import AudiobookConfig
from modules.sub_chapter_splitter import SubChapterSplitter
from modules.sentence_splitter import SentenceSplitter
from modules.audio_generator import AudioGenerator, AudioGeneratorConfig
from modules.subtitle_translator import SubtitleTranslator, SubtitleTranslatorConfig
from modules.statistics_collector import StatisticsCollector
from modules.audio_compressor import AudioCompressor
from modules.vocabulary_manager import VocabularyManager, VocabularyManagerConfig


def get_expected_audio_file(sentence_file: str, output_dir: str) -> str:
    """
    根据句子文件路径推理对应的音频文件路径
    
    Args:
        sentence_file: 句子文件路径 (如 sentences/01_Down_the_Rabbit-Hole(1).txt)
        output_dir: 输出目录
        
    Returns:
        预期的音频文件路径
    """
    filename = os.path.basename(sentence_file)
    audio_filename = os.path.splitext(filename)[0] + '.wav'
    return os.path.join(output_dir, 'audio', audio_filename)


def get_expected_subtitle_file(sentence_file: str, output_dir: str) -> str:
    """
    根据句子文件路径推理对应的字幕文件路径
    
    Args:
        sentence_file: 句子文件路径 (如 sentences/01_Down_the_Rabbit-Hole(1).txt)
        output_dir: 输出目录
        
    Returns:
        预期的字幕文件路径
    """
    filename = os.path.basename(sentence_file)
    subtitle_filename = os.path.splitext(filename)[0] + '.srt'
    return os.path.join(output_dir, 'subtitles', subtitle_filename)


def check_audio_exists(audio_file: str) -> bool:
    """
    检查音频文件是否存在
    
    Args:
        audio_file: 音频文件路径
        
    Returns:
        文件是否存在
    """
    return os.path.exists(audio_file) and os.path.getsize(audio_file) > 0


def check_subtitle_has_chinese(subtitle_file: str) -> bool:
    """
    检查字幕文件是否已包含中文翻译
    
    Args:
        subtitle_file: 字幕文件路径
        
    Returns:
        是否包含中文翻译
    """
    if not os.path.exists(subtitle_file):
        return False
    
    try:
        with open(subtitle_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # 检查是否包含中文字符
            chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
            return bool(chinese_pattern.search(content))
    except Exception:
        return False


def filter_files_for_audio_generation(sentence_files: list, output_dir: str) -> tuple:
    """
    过滤需要生成音频的文件
    
    Args:
        sentence_files: 句子文件列表
        output_dir: 输出目录
        
    Returns:
        (需要处理的文件列表, 跳过的文件数量)
    """
    files_to_process = []
    skipped_count = 0
    
    for sentence_file in sentence_files:
        audio_file = get_expected_audio_file(sentence_file, output_dir)
        
        if check_audio_exists(audio_file):
            skipped_count += 1
        else:
            files_to_process.append(sentence_file)
    
    return files_to_process, skipped_count


def filter_files_for_subtitle_translation(subtitle_files: list) -> tuple:
    """
    过滤需要翻译的字幕文件
    
    Args:
        subtitle_files: 字幕文件列表
        
    Returns:
        (需要处理的文件列表, 跳过的文件数量)
    """
    files_to_process = []
    skipped_count = 0
    
    for subtitle_file in subtitle_files:
        if check_subtitle_has_chinese(subtitle_file):
            skipped_count += 1
        else:
            files_to_process.append(subtitle_file)
    
    return files_to_process, skipped_count


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='章节拆分工具 - 将书籍文本拆分为独立的章节文件',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  %(prog)s data/greens.txt
  %(prog)s data/book.txt --output-dir ./my_output
  %(prog)s data/book.txt --audio --translate --vocabulary
  %(prog)s data/book.txt --vocabulary --master-vocab ./my_vocab.json
  %(prog)s data/book.txt --config my_config.json --verbose
  
默认配置文件: text_to_audiobook/config.json
默认输出目录: ./output
默认总词汇表: script/text_to_audiobook/vocabulary/master_vocabulary.json
输出格式: chapters/, sub_chapters/, sentences/, audio/, subtitles/, vocabulary/ 目录
        """
    )
    
    # 核心参数
    parser.add_argument('input_file',help='输入文本文件路径')
    parser.add_argument('--output-dir', default='./output', help='输出目录路径 (默认: ./output)')
    parser.add_argument('--config', help='配置文件路径 (默认: text_to_audiobook/config.json)')
    parser.add_argument('--verbose','-v',action='store_true',help='显示详细信息')
    
    # 音频生成参数
    parser.add_argument('--audio', action='store_true', help='启用音频生成')
    parser.add_argument('--voice', default='af_bella', help='语音模型 (默认: af_bella)')
    parser.add_argument('--speed', type=float, default=1.0, help='语音速度 (默认: 1.0)')
    
    # 字幕翻译参数
    parser.add_argument('--translate', action='store_true', help='启用字幕翻译')
    
    # 音频压缩参数
    parser.add_argument('--compress', action='store_true', help='启用音频压缩')
    
    # 词汇处理参数
    parser.add_argument('--vocabulary', action='store_true', help='启用词汇提取和分级')
    parser.add_argument('--master-vocab', help='总词汇表文件路径 (默认: script/text_to_audiobook/vocabulary/master_vocabulary.json)')
    
    # 统计参数
    parser.add_argument('--stats', help='启用统计信息收集')

    args = parser.parse_args()
    
    # 验证输入文件
    if not os.path.exists(args.input_file):
        print(f"错误: 输入文件不存在: {args.input_file}")
        return 1
    
    # 创建输出目录
    output_dir = args.output_dir
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        print(f"错误: 无法创建输出目录: {e}")
        return 1
    
    # 记录程序开始时间
    program_start_time = time.time()
    
    try:
        # 加载配置
        config_path = os.path.join(os.path.dirname(__file__), 'config.json') if not args.config else args.config
        config_path = Path(config_path)
        if not os.path.exists(config_path):
            print(f"错误: 配置文件不存在: {config_path}")
            return 1
        
        config = AudiobookConfig.from_json_file(config_path)
        if args.verbose:
            print(f"已加载配置文件: {config_path}")
        
        
        # 创建拆分器并执行拆分
        print(f"\n🔄 开始章节拆分处理...")
        start_time = time.time()
        splitter = ChapterSplitter(config)
        chapter_files = splitter.split_book(args.input_file,output_dir)
        chapter_time = time.time() - start_time
        
        print(f"\n✅ 章节拆分完成! 共生成 {len(chapter_files)} 个章节文件 (耗时: {chapter_time:.2f}秒)")
        
        # 执行子章节拆分
        print(f"\n🔄 开始子章节拆分处理...")
        start_time = time.time()
        sub_splitter = SubChapterSplitter(config.sub_chapter)
        sub_chapter_files = sub_splitter.split_chapters(chapter_files, output_dir)
        sub_chapter_time = time.time() - start_time
        
        print(f"\n✅ 子章节拆分完成! 生成 {len(sub_chapter_files)} 个子章节文件 (耗时: {sub_chapter_time:.2f}秒)")
        
        # 执行句子拆分
        print(f"\n🔄 开始句子拆分处理...")
        start_time = time.time()
        sentence_splitter = SentenceSplitter(config.sentence)
        sentence_files = sentence_splitter.split_files(sub_chapter_files, output_dir)
        sentence_time = time.time() - start_time
        
        print(f"\n✅ 句子拆分完成! 最终生成 {len(sentence_files)} 个句子文件 (耗时: {sentence_time:.2f}秒)")
        
        # 执行音频生成（可选）
        audio_files = []
        subtitle_files = []
        audio_time = 0
        if args.audio:
            print(f"\n🔊 开始音频生成处理...")
            
            # 过滤需要生成音频的文件
            files_to_process, skipped_count = filter_files_for_audio_generation(sentence_files, output_dir)
            
            if skipped_count > 0:
                print(f"📋 跳过 {skipped_count} 个已存在的音频文件")
            
            if files_to_process:
                print(f"🎵 需要生成 {len(files_to_process)} 个音频文件")
                start_time = time.time()
                try:
                    audio_config = AudioGeneratorConfig(voice=args.voice, speed=args.speed)
                    audio_generator = AudioGenerator(audio_config)
                    audio_files, subtitle_files = audio_generator.generate_audio_files(files_to_process, output_dir)
                    audio_time = time.time() - start_time
                    
                    total_audio_files = len(audio_files) + skipped_count
                    total_subtitle_files = len(subtitle_files) + skipped_count
                    print(f"\n✅ 音频生成完成! 总计 {total_audio_files} 个音频文件 (新生成 {len(audio_files)} 个) 和 {total_subtitle_files} 个字幕文件 (新生成 {len(subtitle_files)} 个) (耗时: {audio_time:.2f}秒)")
                except Exception as e:
                    audio_time = time.time() - start_time
                    print(f"\n⚠️ 音频生成失败: {e} (耗时: {audio_time:.2f}秒)")
                    if args.verbose:
                        import traceback
                        traceback.print_exc()
                    print("继续执行其他步骤...")
            else:
                print(f"✅ 所有音频文件已存在，跳过音频生成步骤")
                # 收集所有音频和字幕文件（包括已存在的）
                for sentence_file in sentence_files:
                    audio_file = get_expected_audio_file(sentence_file, output_dir)
                    subtitle_file = get_expected_subtitle_file(sentence_file, output_dir)
                    if check_audio_exists(audio_file):
                        audio_files.append(audio_file)
                    if os.path.exists(subtitle_file):
                        subtitle_files.append(subtitle_file)
        
        # 执行字幕翻译（可选）
        translated_files = []
        translate_time = 0
        if args.translate and subtitle_files:
            print(f"\n🌏 开始字幕翻译处理...")
            
            # 过滤需要翻译的字幕文件
            files_to_translate, skipped_count = filter_files_for_subtitle_translation(subtitle_files)
            
            if skipped_count > 0:
                print(f"📋 跳过 {skipped_count} 个已包含中文翻译的字幕文件")
            
            if files_to_translate:
                print(f"🌐 需要翻译 {len(files_to_translate)} 个字幕文件")
                start_time = time.time()
                try:
                    # 配置翻译器
                    translator_config = config.subtitle_translator                
                    if not translator_config.api_key:
                        raise RuntimeError("缺少 SiliconFlow API 密钥，请通过 --api-key 参数或配置文件提供")
                    
                    translator = SubtitleTranslator(translator_config)
                    translated_files = translator.translate_subtitle_files(files_to_translate)
                    translate_time = time.time() - start_time
                    
                    total_translated = len(translated_files) + skipped_count
                    print(f"\n✅ 字幕翻译完成! 总计 {total_translated} 个字幕文件包含中文翻译 (新翻译 {len(translated_files)} 个) (耗时: {translate_time:.2f}秒)")
                except Exception as e:
                    translate_time = time.time() - start_time
                    print(f"\n⚠️ 字幕翻译失败: {e} (耗时: {translate_time:.2f}秒)")
                    if args.verbose:
                        import traceback
                        traceback.print_exc()
                    print("继续执行其他步骤...")
            else:
                print(f"✅ 所有字幕文件已包含中文翻译，跳过翻译步骤")
                translated_files = subtitle_files  # 所有文件都已翻译
        elif args.translate and not subtitle_files:
            print(f"\n⚠️ 未找到字幕文件，跳过翻译步骤（请先启用 --audio 生成字幕）")

        # 执行音频压缩（可选）
        compression_time = 0
        if args.compress and audio_files:
            print(f"\n🗜️ 开始音频压缩处理...")
            start_time = time.time()
            try:
                # 获取压缩配置
                compression_config = config.audio_compression
                compressor = AudioCompressor(compression_config.__dict__)
                
                # 压缩音频文件
                compression_results = compressor.compress_book_audio(output_dir, compression_config.output_subdir)
                compression_time = time.time() - start_time
                
                print(f"\n✅ 音频压缩完成! (耗时: {compression_time:.2f}秒)")
                
                if args.verbose and compression_results:
                    print(f"📊 压缩统计:")
                    for format_name, stats in compression_results.items():
                        print(f"  {format_name.upper()}: {stats['files_success']}/{stats['files_processed']} 文件, 压缩比 {stats['compression_ratio']:.1f}%")
                
            except Exception as e:
                compression_time = time.time() - start_time
                print(f"\n⚠️ 音频压缩失败: {e} (耗时: {compression_time:.2f}秒)")
                if args.verbose:
                    import traceback
                    traceback.print_exc()
                print("继续执行其他步骤...")
        elif args.compress and not audio_files:
            print(f"\n⚠️ 未找到音频文件，跳过压缩步骤（请先启用 --audio 生成音频）")
        
        # 执行词汇提取（可选）
        vocabulary_time = 0
        chapter_vocab_files = []
        if args.vocabulary and sentence_files:
            print(f"\n📚 开始词汇提取和分级处理...")
            start_time = time.time()
            try:
                # 获取书籍名称
                book_name = os.path.splitext(os.path.basename(args.input_file))[0]
                
                # 配置词汇管理器
                vocab_config = VocabularyManagerConfig()
                
                # 设置API密钥（如果需要）
                if config.subtitle_translator.api_key:
                    vocab_config.enrichment.siliconflow_api_key = config.subtitle_translator.api_key
                
                vocab_manager = VocabularyManager(vocab_config)
                
                # 处理词汇
                chapter_vocab_files = vocab_manager.process_book_vocabulary(
                    sentence_files=sentence_files,
                    output_dir=output_dir,
                    book_name=book_name,
                    master_vocab_path=args.master_vocab
                )
                
                vocabulary_time = time.time() - start_time
                print(f"\n✅ 词汇处理完成! 生成 {len(chapter_vocab_files)} 个章节词汇文件 (耗时: {vocabulary_time:.2f}秒)")
                
                # 显示词汇统计
                if args.verbose:
                    stats = vocab_manager.get_vocabulary_stats(args.master_vocab or vocab_config.default_master_vocab_path)
                    if stats:
                        print(f"📊 总词汇表统计:")
                        print(f"  总词汇数: {stats.get('total_words', 0)}")
                        if 'level_distribution' in stats:
                            for level_name, count in stats['level_distribution'].items():
                                print(f"  {level_name}: {count}词")
                
            except Exception as e:
                vocabulary_time = time.time() - start_time
                print(f"\n⚠️ 词汇处理失败: {e} (耗时: {vocabulary_time:.2f}秒)")
                if args.verbose:
                    import traceback
                    traceback.print_exc()
                print("继续执行其他步骤...")
        elif args.vocabulary and not sentence_files:
            print(f"\n⚠️ 未找到句子文件，跳过词汇处理步骤")
        
        # 执行统计信息收集（如果启用且有音频文件）
        statistics_time = 0
        if args.stats and audio_files:
            print(f"\n📊 开始统计信息收集...")
            start_time = time.time()
            try:
                statistics_collector = StatisticsCollector(config.statistics)
                
                # 收集统计信息（如果有翻译器就传入用于翻译章节标题）
                translator_for_stats = None
                if args.translate and config.subtitle_translator.api_key:
                    translator_for_stats = SubtitleTranslator(config.subtitle_translator)
                
                statistics = statistics_collector.collect_statistics(
                    sub_chapter_files=sub_chapter_files,
                    audio_files=audio_files,
                    output_dir=output_dir,
                    translator=translator_for_stats
                )
                
                statistics_time = time.time() - start_time
                print(f"\n✅ 统计信息收集完成! (耗时: {statistics_time:.2f}秒)")
                
                if args.verbose and statistics:
                    book_info = statistics.get('book', {})
                    chapters_info = statistics.get('chapters', [])
                    print(f"📖 书籍信息: {book_info.get('title', 'Unknown')} (共 {book_info.get('total_chapters', 0)} 章节, 总时长 {book_info.get('total_duration', 0):.1f}秒)")
                    print(f"📊 收集了 {len(chapters_info)} 个章节的统计信息")
                
            except Exception as e:
                statistics_time = time.time() - start_time
                print(f"\n⚠️ 统计信息收集失败: {e} (耗时: {statistics_time:.2f}秒)")
                if args.verbose:
                    import traceback
                    traceback.print_exc()
                print("继续执行其他步骤...")
        elif config.statistics.enabled and not audio_files:
            print(f"\n⚠️ 未找到音频文件，跳过统计收集步骤（请先启用 --audio 生成音频）")
        
        # 计算总耗时
        total_time = chapter_time + sub_chapter_time + sentence_time + audio_time + translate_time + vocabulary_time + statistics_time
        program_total_time = time.time() - program_start_time
        
        # 打印耗时汇总
        print(f"\n📊 执行耗时汇总:")
        print(f"  章节拆分: {chapter_time:.2f}秒 ({chapter_time/total_time*100:.1f}%)")
        print(f"  子章节拆分: {sub_chapter_time:.2f}秒 ({sub_chapter_time/total_time*100:.1f}%)")
        print(f"  句子拆分: {sentence_time:.2f}秒 ({sentence_time/total_time*100:.1f}%)")
        if args.audio:
            print(f"  音频生成: {audio_time:.2f}秒 ({audio_time/total_time*100:.1f}%)")
        if args.translate:
            print(f"  字幕翻译: {translate_time:.2f}秒 ({translate_time/total_time*100:.1f}%)")
        if args.vocabulary:
            print(f"  词汇处理: {vocabulary_time:.2f}秒 ({vocabulary_time/total_time*100:.1f}%)")
        if config.statistics.enabled and statistics_time > 0:
            print(f"  统计收集: {statistics_time:.2f}秒 ({statistics_time/total_time*100:.1f}%)")
        print(f"  核心处理总耗时: {total_time:.2f}秒")
        print(f"  程序总耗时: {program_total_time:.2f}秒")
        
        if args.verbose:
            # 从第一个句子文件获取实际输出目录
            if sentence_files:
                actual_output_dir = os.path.dirname(sentence_files[0])
                print(f"\n输出目录: {actual_output_dir}")
            print("生成的句子文件:")
            for file_path in sentence_files:
                print(f"  - {os.path.basename(file_path)}")
            
            # 显示音频文件信息（如果生成）
            if args.audio and audio_files:
                print("生成的音频文件:")
                for file_path in audio_files:
                    print(f"  - {os.path.basename(file_path)}")
                print("生成的字幕文件:")
                for file_path in subtitle_files:
                    print(f"  - {os.path.basename(file_path)}")
            
            # 显示翻译文件信息（如果翻译）
            if args.translate and translated_files:
                print("翻译的字幕文件:")
                for file_path in translated_files:
                    print(f"  - {os.path.basename(file_path)} (已包含中文翻译)")
            
            # 显示词汇文件信息（如果处理）
            if args.vocabulary and chapter_vocab_files:
                print("生成的章节词汇文件:")
                for file_path in chapter_vocab_files:
                    print(f"  - {os.path.basename(file_path)}")
        
        return 0
        
    except Exception as e:
        print(f"❌ 拆分失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())