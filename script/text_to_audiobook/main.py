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



def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='章节拆分工具 - 将书籍文本拆分为独立的章节文件',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  %(prog)s data/greens.txt
  %(prog)s data/book.txt --output-dir ./my_output
  %(prog)s data/book.txt --audio --parse --vocabulary
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
    parser.add_argument('--verbose','-v',action='store_true',help='显示详细信息')
    
    # 章节拆分
    parser.add_argument('--split', action='store_true', help='启用章节拆分')

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

    # 默认目录
    program_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    file_name = os.path.basename(args.input_file)
    output_dir = os.path.join(program_root, "output", os.path.splitext(file_name)[0])
    master_vocab_file = os.path.join(program_root, "output", "vocabulary", "master_vocabulary.json")
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')

    # 验证输入文件
    if not os.path.exists(args.input_file):
        print(f"错误: 输入文件不存在: {args.input_file}")
        return 1
    
    # 创建输出目录
    try:
        os.makedirs(output_dir, exist_ok=True)
    except Exception as e:
        print(f"错误: 无法创建输出目录: {e}")
        return 1
    
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
        
        # 执行各个处理流程
        chapter_files, sub_chapter_files, sentence_files = [], [], []
        chapter_time, sub_chapter_time, sentence_time = 0, 0, 0
        if args.split:
            # 使用统一的文本处理流程
            chapter_files, sub_chapter_files, sentence_files, text_processing_time = workflow.execute_text_processing(args.input_file, output_dir, args.verbose)
            chapter_time = sub_chapter_time = sentence_time = text_processing_time / 3  # 平均分配时间
        else:
            # 获取已存在的文件
            from util.file_utils import get_existing_files
            chapter_files = get_existing_files(output_dir, OUTPUT_DIRECTORIES['chapters'], ".txt")
            sub_chapter_files = get_existing_files(output_dir, OUTPUT_DIRECTORIES['sub_chapters'], ".txt") 
            sentence_files = get_existing_files(output_dir, OUTPUT_DIRECTORIES['sentences'], ".txt")
        
        # 音频生成
        audio_files, subtitle_files, audio_time = [], [], 0
        if args.audio:
            audio_files, subtitle_files, audio_time = workflow.execute_audio_processing(sentence_files, output_dir, args.voice, args.speed, True, args.verbose)
        else:
            from util.file_utils import get_existing_files
            audio_files = get_existing_files(output_dir, OUTPUT_DIRECTORIES['audio'], ".wav")
            subtitle_files = get_existing_files(output_dir, OUTPUT_DIRECTORIES['subtitles'], ".srt")

        # 字幕解析和翻译
        parsed_files, parse_time = [], 0
        if args.parse:
            parsed_files, parse_time = workflow.execute_translation_and_analysis(subtitle_files, sub_chapter_files, audio_files, output_dir, args.verbose)

        # 词汇处理
        chapter_vocab_files, vocabulary_time = [], 0
        if args.vocabulary:
            book_name = os.path.splitext(os.path.basename(args.input_file))[0]
            chapter_vocab_files, vocabulary_time = workflow.execute_vocabulary_processing(sentence_files, output_dir, book_name, master_vocab_file, args.verbose)
        
        # 统计信息收集
        statistics_time = 0
        if args.stats:
            # 独立收集统计信息
            statistics, statistics_time = workflow.execute_statistics_collection(sub_chapter_files, audio_files, output_dir, args.verbose)
        
        # 计算总耗时
        total_time = chapter_time + sub_chapter_time + sentence_time + audio_time + parse_time + vocabulary_time + statistics_time
        program_total_time = time.time() - program_start_time
        
        # 打印耗时汇总
        print(f"\n📊 执行耗时汇总:")
        if args.split:
            print(f"  文本处理: {chapter_time + sub_chapter_time + sentence_time:.2f}秒 ({(chapter_time + sub_chapter_time + sentence_time)/total_time*100:.1f}%)")
        if args.audio:
            print(f"  音频生成: {audio_time:.2f}秒 ({audio_time/total_time*100:.1f}%)")
        if args.parse:
            print(f"  翻译和分析: {parse_time:.2f}秒 ({parse_time/total_time*100:.1f}%)")
        if args.vocabulary:
            print(f"  词汇处理: {vocabulary_time:.2f}秒 ({vocabulary_time/total_time*100:.1f}%)")
        if args.stats and statistics_time > 0:
            print(f"  统计收集: {statistics_time:.2f}秒 ({statistics_time/total_time*100:.1f}%)")
        print(f"  核心处理总耗时: {total_time:.2f}秒")
        print(f"  程序总耗时: {program_total_time:.2f}秒")
        
        if args.verbose:
            # 显示输出目录和文件信息
            print(f"\n输出目录: {output_dir}")
            print(f"生成的句子文件: {len(sentence_files)} 个")
            
            if args.audio and audio_files:
                print(f"生成的音频文件: {len(audio_files)} 个")
                print(f"生成的字幕文件: {len(subtitle_files)} 个")
            
            if args.parse and parsed_files:
                print(f"解析的字幕文件: {len(parsed_files)} 个")
            
            if args.vocabulary and chapter_vocab_files:
                print(f"生成的章节词汇文件: {len(chapter_vocab_files)} 个")
        
        return 0
        
    except Exception as e:
        print(f"❌ 拆分失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())