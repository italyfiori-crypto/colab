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

from infra.config_loader import ConfigLoader
from service.workflow_executor import WorkflowExecutor
from util import OUTPUT_DIRECTORIES
from util.file_utils import find_txt_files


def process_single_file(input_file: str, args, config: dict, workflow: 'WorkflowExecutor') -> dict:
    """
    处理单个文件
    
    Returns:
        包含处理结果和统计信息的字典
    """
    # 默认目录
    program_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    file_name = os.path.basename(input_file)
    output_dir = os.path.join(program_root, "output", os.path.splitext(file_name)[0])
    master_vocab_file = os.path.join(program_root, "output", "vocabulary", "master_vocabulary.json")

    # 创建输出目录
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        raise Exception(f"无法创建输出目录: {e}")
    
    if args.verbose:
        print(f"\n📁 处理文件: {input_file}")
        print(f"📂 输出目录: {output_dir}")
    
    # 记录文件处理开始时间
    file_start_time = time.time()
    
    # 执行各个处理流程
    sub_chapter_files, sentence_files = [], []
    chapter_time, sentence_time = 0, 0
    
    # 章节和子章节拆分
    if args.chapter:
        _, sub_chapter_files, chapter_time = workflow.execute_chapter_processing(input_file, output_dir, args.verbose)
    else:
        # 获取已存在的子章节文件
        from util.file_utils import get_existing_files
        sub_chapter_files = get_existing_files(output_dir, OUTPUT_DIRECTORIES['sub_chapters'], ".txt")
    
    # 句子拆分
    if args.sentence:
        if not sub_chapter_files:
            raise Exception("未找到子章节文件，请先运行 --chapter 进行章节拆分")
        sentence_files, sentence_time = workflow.execute_sentence_processing(sub_chapter_files, output_dir, args.verbose)
    else:
        # 获取已存在的句子文件
        from util.file_utils import get_existing_files
        sentence_files = get_existing_files(output_dir, OUTPUT_DIRECTORIES['sentences'], ".txt")
    
    # 音频生成
    audio_files, subtitle_files, audio_time = [], [], 0
    if args.audio:
        audio_files, subtitle_files, audio_time = workflow.execute_audio_processing(sentence_files, output_dir, args.voice, args.speed, args.verbose)
    else:
        from util.file_utils import get_existing_files
        audio_files = get_existing_files(output_dir, OUTPUT_DIRECTORIES['audio'], ".wav")
        subtitle_files = get_existing_files(output_dir, OUTPUT_DIRECTORIES['subtitles'], ".srt")

    # 字幕解析和翻译
    parsed_files, parse_time = [], 0
    if args.parse:
        parsed_files, parse_time = workflow.execute_translation_and_analysis(subtitle_files, sub_chapter_files, audio_files, output_dir, args.verbose)

    # 音频压缩
    compressed_files, compression_time = [], 0
    if args.compress:
        if not audio_files:
            print("⚠️  警告: 未找到音频文件，请先运行 --audio 进行音频生成")
        else:
            compressed_files, compression_time = workflow.execute_audio_compression(audio_files, output_dir, args.verbose)

    # 词汇处理
    chapter_vocab_files, vocabulary_time = [], 0
    if args.vocabulary:
        book_name = os.path.splitext(os.path.basename(input_file))[0]
        chapter_vocab_files, vocabulary_time = workflow.execute_vocabulary_processing(sentence_files, output_dir, book_name, master_vocab_file, args.verbose)
    
    # 统计信息收集
    statistics_time = 0
    if args.stats:
        # 独立收集统计信息
        _, statistics_time = workflow.execute_statistics_collection(sub_chapter_files, audio_files, output_dir, args.verbose)
    
    # 计算耗时
    total_time = chapter_time + sentence_time + audio_time + parse_time + compression_time + vocabulary_time + statistics_time
    file_total_time = time.time() - file_start_time
    
    return {
        'input_file': input_file,
        'output_dir': output_dir,
        'success': True,
        'times': {
            'chapter': chapter_time,
            'sentence': sentence_time,
            'audio': audio_time,
            'parse': parse_time,
            'compression': compression_time,
            'vocabulary': vocabulary_time,
            'statistics': statistics_time,
            'total': total_time,
            'file_total': file_total_time
        },
        'files': {
            'sentence_files': len(sentence_files),
            'audio_files': len(audio_files),
            'subtitle_files': len(subtitle_files),
            'compressed_files': len(compressed_files),
            'parsed_files': len(parsed_files),
            'chapter_vocab_files': len(chapter_vocab_files)
        }
    }


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='章节拆分工具 - 将书籍文本拆分为独立的章节文件',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  %(prog)s data/greens.txt
  %(prog)s data/books/  # 批量处理目录下所有.txt文件
  %(prog)s data/book.txt --chapter --sentence
  %(prog)s data/book.txt --chapter --sentence --audio --parse --vocabulary
  %(prog)s data/book.txt --sentence --audio  # 只运行句子拆分和音频生成
  %(prog)s data/book.txt --chapter  # 只运行章节拆分
  
默认配置文件: text_to_audiobook/config.json
默认输出目录: ./output
默认总词汇表: script/text_to_audiobook/vocabulary/master_vocabulary.json
输出格式: chapters/, sub_chapters/, sentences/, audio/, subtitles/, vocabulary/ 目录
        """
    )
    
    # 核心参数
    parser.add_argument('input_path',help='输入文本文件或目录路径')
    parser.add_argument('--verbose','-v',action='store_true',help='显示详细信息')
    
    # 文本拆分参数
    parser.add_argument('--chapter', action='store_true', help='启用章节和子章节拆分')
    parser.add_argument('--sentence', action='store_true', help='启用句子拆分')

    # 音频生成参数
    parser.add_argument('--audio', action='store_true', help='启用音频生成')
    parser.add_argument('--voice', default='af_bella', help='语音模型 (默认: af_bella)')
    parser.add_argument('--speed', type=float, default=0.8, help='语音速度 (默认: 1.0)')
    
    # 字幕解析参数
    parser.add_argument('--parse', action='store_true', help='启用字幕解析')
    
    # 音频压缩参数
    parser.add_argument('--compress', action='store_true', help='启用音频压缩')
    
    # 词汇处理参数
    parser.add_argument('--vocabulary', action='store_true', help='启用词汇提取和分级')
    
    # 统计参数
    parser.add_argument('--stats', action='store_true', help='启用统计信息收集')
    args = parser.parse_args()

    # 配置路径
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')

    # 发现待处理的文件
    try:
        input_files = find_txt_files(args.input_path)
    except ValueError as e:
        print(f"错误: {e}")
        return 1
    
    # 显示发现的文件
    print(f"🔍 发现 {len(input_files)} 个 .txt 文件:")
    for i, file in enumerate(input_files, 1):
        print(f"  {i}. {os.path.basename(file)}")
    
    # 记录程序开始时间
    program_start_time = time.time()
    
    try:
        # 加载配置
        if not os.path.exists(config_path):
            print(f"错误: 配置文件不存在: {config_path}")
            return 1
        
        config_loader = ConfigLoader()
        config = config_loader.load_config(config_path)
        if args.verbose:
            print(f"已加载配置文件: {config_path}")
        
        # 初始化工作流执行器
        workflow = WorkflowExecutor(config)
        
        # 批量处理文件
        results = []
        for i, input_file in enumerate(input_files, 1):
            print(f"\n🚀 [{i}/{len(input_files)}] 开始处理: {os.path.basename(input_file)}")
            
            try:
                result = process_single_file(input_file, args, config, workflow)
                results.append(result)
                print(f"✅ [{i}/{len(input_files)}] 处理完成: {os.path.basename(input_file)} ({result['times']['file_total']:.2f}秒)")
                
            except Exception as e:
                error_result = {
                    'input_file': input_file,
                    'success': False,
                    'error': str(e)
                }
                results.append(error_result)
                print(f"❌ [{i}/{len(input_files)}] 处理失败: {os.path.basename(input_file)} - {e}")
                if args.verbose:
                    import traceback
                    traceback.print_exc()
        
        # 计算总体统计
        program_total_time = time.time() - program_start_time
        successful_results = [r for r in results if r['success']]
        failed_results = [r for r in results if not r['success']]
        
        # 汇总所有成功处理的时间
        if successful_results:
            total_times = {
                'chapter': sum(r['times']['chapter'] for r in successful_results),
                'sentence': sum(r['times']['sentence'] for r in successful_results),
                'audio': sum(r['times']['audio'] for r in successful_results),
                'parse': sum(r['times']['parse'] for r in successful_results),
                'compression': sum(r['times']['compression'] for r in successful_results),
                'vocabulary': sum(r['times']['vocabulary'] for r in successful_results),
                'statistics': sum(r['times']['statistics'] for r in successful_results),
                'total': sum(r['times']['total'] for r in successful_results)
            }
            
            # 打印批量处理汇总
            print(f"\n📊 批量处理汇总 ({len(successful_results)}/{len(input_files)} 成功):")
            if args.chapter and total_times['total'] > 0:
                print(f"  章节拆分: {total_times['chapter']:.2f}秒 ({total_times['chapter']/total_times['total']*100:.1f}%)")
            if args.sentence and total_times['total'] > 0:
                print(f"  句子拆分: {total_times['sentence']:.2f}秒 ({total_times['sentence']/total_times['total']*100:.1f}%)")
            if args.audio and total_times['total'] > 0:
                print(f"  音频生成: {total_times['audio']:.2f}秒 ({total_times['audio']/total_times['total']*100:.1f}%)")
            if args.parse and total_times['total'] > 0:
                print(f"  翻译和分析: {total_times['parse']:.2f}秒 ({total_times['parse']/total_times['total']*100:.1f}%)")
            if args.compress and total_times['total'] > 0:
                print(f"  音频压缩: {total_times['compression']:.2f}秒 ({total_times['compression']/total_times['total']*100:.1f}%)")
            if args.vocabulary and total_times['total'] > 0:
                print(f"  词汇处理: {total_times['vocabulary']:.2f}秒 ({total_times['vocabulary']/total_times['total']*100:.1f}%)")
            if args.stats and total_times['statistics'] > 0:
                print(f"  统计收集: {total_times['statistics']:.2f}秒 ({total_times['statistics']/total_times['total']*100:.1f}%)")
            print(f"  核心处理总耗时: {total_times['total']:.2f}秒")
            print(f"  程序总耗时: {program_total_time:.2f}秒")
            
            if args.verbose:
                # 显示详细统计
                total_files = {
                    'sentence_files': sum(r['files']['sentence_files'] for r in successful_results),
                    'audio_files': sum(r['files']['audio_files'] for r in successful_results),
                    'subtitle_files': sum(r['files']['subtitle_files'] for r in successful_results),
                    'compressed_files': sum(r['files']['compressed_files'] for r in successful_results),
                    'parsed_files': sum(r['files']['parsed_files'] for r in successful_results),
                    'chapter_vocab_files': sum(r['files']['chapter_vocab_files'] for r in successful_results)
                }
                
                print(f"\n📁 生成文件统计:")
                print(f"  生成的句子文件: {total_files['sentence_files']} 个")
                if args.audio and total_files['audio_files'] > 0:
                    print(f"  生成的音频文件: {total_files['audio_files']} 个")
                    print(f"  生成的字幕文件: {total_files['subtitle_files']} 个")
                if args.compress and total_files['compressed_files'] > 0:
                    print(f"  压缩的音频文件: {total_files['compressed_files']} 个")
                if args.parse and total_files['parsed_files'] > 0:
                    print(f"  解析的字幕文件: {total_files['parsed_files']} 个")
                if args.vocabulary and total_files['chapter_vocab_files'] > 0:
                    print(f"  生成的章节词汇文件: {total_files['chapter_vocab_files']} 个")
        
        # 显示失败的文件
        if failed_results:
            print(f"\n❌ 失败的文件 ({len(failed_results)} 个):")
            for result in failed_results:
                print(f"  • {os.path.basename(result['input_file'])}: {result['error']}")
        
        # 返回状态码
        return 1 if failed_results else 0
        
    except Exception as e:
        print(f"❌ 批量处理失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())