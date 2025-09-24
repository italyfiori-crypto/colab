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
from util.file_utils import get_existing_files


def extract_paths_from_sub_chapter(sub_chapter_file: str) -> tuple[str, str, str]:
    """
    从子章节文件路径提取必要信息
    
    Args:
        sub_chapter_file: 子章节文件路径
        例如: /path/to/output/book_name/sub_chapters/chapter_01_001.txt
        
    Returns:
        (output_dir, book_name, base_name)
        - output_dir: /path/to/output/book_name/
        - book_name: book_name  
        - base_name: chapter_01_001
    """
    # 标准化路径
    sub_chapter_file = os.path.abspath(sub_chapter_file)
    
    # 验证文件路径包含sub_chapters
    if 'sub_chapters' not in sub_chapter_file:
        raise ValueError(f"文件不在sub_chapters目录中: {sub_chapter_file}")
    
    # 提取基础文件名（不含扩展名）
    base_name = os.path.splitext(os.path.basename(sub_chapter_file))[0]
    
    # 获取输出目录（sub_chapters的父目录）
    sub_chapters_dir = os.path.dirname(sub_chapter_file)
    output_dir = os.path.dirname(sub_chapters_dir)
    
    # 提取书籍名称（输出目录的最后一级）
    book_name = os.path.basename(output_dir)
    
    return output_dir, book_name, base_name


def cleanup_sub_chapter_files(sub_chapter_file: str, output_dir: str, verbose: bool = False):
    """
    清理子章节对应的相关文件
    
    Args:
        sub_chapter_file: 子章节文件路径
        output_dir: 输出目录
        verbose: 是否显示详细信息
    """
    _, _, base_name = extract_paths_from_sub_chapter(sub_chapter_file)
    
    # 定义需要清理的文件路径
    files_to_clean = [
        os.path.join(output_dir, OUTPUT_DIRECTORIES['sentences'], f"{base_name}.jsonl"),
        os.path.join(output_dir, OUTPUT_DIRECTORIES['audio'], f"{base_name}.wav"),
        os.path.join(output_dir, OUTPUT_DIRECTORIES['subtitles'], f"{base_name}.jsonl"),
        os.path.join(output_dir, OUTPUT_DIRECTORIES['analysis'], f"{base_name}.jsonl"),
        os.path.join(output_dir, OUTPUT_DIRECTORIES['compressed_audio'], f"{base_name}.mp3"),
    ]
    
    cleaned_count = 0
    for file_path in files_to_clean:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                cleaned_count += 1
                if verbose:
                    print(f"  🗑️  删除: {os.path.relpath(file_path, output_dir)}")
            except Exception as e:
                print(f"  ❌ 删除失败 {os.path.relpath(file_path, output_dir)}: {e}")
    
    if verbose and cleaned_count > 0:
        print(f"🧹 已清理 {cleaned_count} 个相关文件")
    elif verbose:
        print("🧹 未找到需要清理的文件")

def process_single_book(input_file: str, args, config: dict, workflow: 'WorkflowExecutor') -> dict:
    """
    处理单本书籍文件（从原始文本开始的完整流程）
    
    Args:
        input_file: 书籍文本文件路径
        args: 命令行参数
        config: 配置信息
        workflow: 工作流执行器
        
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
        sub_chapter_files = get_existing_files(output_dir, OUTPUT_DIRECTORIES['sub_chapters'], ".txt")
    
    # 句子拆分
    if args.sentence:
        if not sub_chapter_files:
            raise Exception("未找到子章节文件，请先运行 --chapter 进行章节拆分")
        sentence_files, sentence_time = workflow.execute_sentence_processing(sub_chapter_files, output_dir, args.verbose)
    else:
        # 获取已存在的句子文件
        sentence_files = get_existing_files(output_dir, OUTPUT_DIRECTORIES['sentences'], ".jsonl")
    
    # 音频&字幕生成
    audio_files, subtitle_files, audio_time = [], [], 0
    if args.audio:
        audio_files, subtitle_files, audio_time = workflow.execute_audio_processing(sentence_files, output_dir, args.voice, args.speed, args.verbose)
    else:
        audio_files = get_existing_files(output_dir, OUTPUT_DIRECTORIES['audio'], ".wav")
        subtitle_files = get_existing_files(output_dir, OUTPUT_DIRECTORIES['subtitles'], ".jsonl")

    # 分析处理
    analyzed_files, analysis_time = [], 0
    if args.analysis:
        analyzed_files, analysis_time = workflow.execute_analysis(subtitle_files, output_dir, args.verbose)

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
        chapter_vocab_files, vocabulary_time = workflow.execute_vocabulary_processing(sub_chapter_files, output_dir, book_name, master_vocab_file, args.verbose)
    
    # 统计信息收集
    statistics_time = 0
    if args.stats:
        # 独立收集统计信息
        _, statistics_time = workflow.execute_statistics_collection(sub_chapter_files, audio_files, output_dir, args.verbose)
    
    # 计算耗时
    total_time = chapter_time + sentence_time + audio_time + analysis_time + compression_time + vocabulary_time + statistics_time
    file_total_time = time.time() - file_start_time
    
    return {
        'input_file': input_file,
        'output_dir': output_dir,
        'success': True,
        'times': {
            'chapter': chapter_time,
            'sentence': sentence_time,
            'audio': audio_time,
            'analysis': analysis_time,
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
            'analyzed_files': len(analyzed_files),
            'chapter_vocab_files': len(chapter_vocab_files)
        }
    }


def process_single_sub_chapter(sub_chapter_file: str, args, config: dict, workflow: 'WorkflowExecutor') -> dict:
    """
    处理单个子章节文件（从句子拆分开始的流程）
    
    Args:
        sub_chapter_file: 子章节文件路径
        args: 命令行参数
        config: 配置信息
        workflow: 工作流执行器
        
    Returns:
        包含处理结果和统计信息的字典
    """
    try:
        # 路径解析
        output_dir, book_name, base_name = extract_paths_from_sub_chapter(sub_chapter_file)
        master_vocab_file = os.path.join(os.path.dirname(output_dir), "vocabulary", "master_vocabulary.json")
        
        if args.verbose:
            print(f"\n📁 处理子章节: {sub_chapter_file}")
            print(f"📂 输出目录: {output_dir}")
            print(f"📖 书籍名称: {book_name}")
            print(f"📄 章节名称: {base_name}")
        
        # 文件清理（如果启用覆盖模式）
        if args.overwrite:
            print(f"🧹 清理子章节相关文件...")
            cleanup_sub_chapter_files(sub_chapter_file, output_dir, args.verbose)
        
        # 记录处理开始时间
        start_time = time.time()
        
        # 初始化计时变量
        sentence_time, audio_time, analysis_time = 0, 0, 0
        compression_time, vocabulary_time, statistics_time = 0, 0, 0
        
        # 句子拆分（必须执行，因为是从子章节开始）
        sentence_files = []
        if args.sentence:
            sentence_files, sentence_time = workflow.execute_sentence_processing([sub_chapter_file], output_dir, args.verbose)
        else:
            # 获取已存在的句子文件
            sentence_files = get_existing_files(output_dir, OUTPUT_DIRECTORIES['sentences'], ".jsonl")
            if not sentence_files and args.verbose:
                print("⚠️ 未找到对应的句子文件，请先运行 --sentence 进行句子拆分")
        
        # 音频生成
        audio_files, subtitle_files = [], []
        if args.audio and sentence_files:
            audio_files, subtitle_files, audio_time = workflow.execute_audio_processing(sentence_files, output_dir, args.voice, args.speed, args.verbose)
        else:
            # 获取已存在的音频和字幕文件
            audio_files = [os.path.join(output_dir, OUTPUT_DIRECTORIES['audio'], f"{base_name}.wav")] if os.path.exists(os.path.join(output_dir, OUTPUT_DIRECTORIES['audio'], f"{base_name}.wav")) else []
            subtitle_files = [os.path.join(output_dir, OUTPUT_DIRECTORIES['subtitles'], f"{base_name}.jsonl")] if os.path.exists(os.path.join(output_dir, OUTPUT_DIRECTORIES['subtitles'], f"{base_name}.jsonl")) else []
        
        # 分析处理
        analyzed_files = []
        if args.analysis and subtitle_files:
            analyzed_files, analysis_time = workflow.execute_analysis(subtitle_files, output_dir, args.verbose)

        # 音频压缩
        compressed_files = []
        if args.compress and audio_files:
            compressed_files, compression_time = workflow.execute_audio_compression(audio_files, output_dir, args.verbose)

        # 词汇处理
        chapter_vocab_files = []
        if args.vocabulary and sentence_files:
            chapter_vocab_files, vocabulary_time = workflow.execute_vocabulary_processing([sub_chapter_file], output_dir, book_name, master_vocab_file, args.verbose)
        
        # 统计信息收集（仅针对单个子章节的统计）
        if args.stats:
            # 对于单个子章节，只收集当前处理的统计
            _, statistics_time = workflow.execute_statistics_collection([sub_chapter_file], audio_files, output_dir, args.verbose)
        
        # 计算耗时
        total_time = sentence_time + audio_time + analysis_time + compression_time + vocabulary_time + statistics_time
        file_total_time = time.time() - start_time
        
        return {
            'input_file': sub_chapter_file,
            'output_dir': output_dir,
            'book_name': book_name,
            'base_name': base_name,
            'success': True,
            'times': {
                'sentence': sentence_time,
                'audio': audio_time,
                'analysis': analysis_time,
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
                'analyzed_files': len(analyzed_files),
                'chapter_vocab_files': len(chapter_vocab_files)
            }
        }
        
    except Exception as e:
        return {
            'input_file': sub_chapter_file,
            'success': False,
            'error': str(e)
        }


def print_sub_chapter_results(results: list[dict]):
    """专门为子章节处理结果输出"""
    if not results:
        return
    
    result = results[0]  # 单个子章节结果
    if not result['success']:
        return
    
    print(f"\n📊 子章节处理完成:")
    print(f"  📖 书籍: {result['book_name']}")
    print(f"  📄 章节: {result['base_name']}")
    print(f"  📂 输出目录: {result['output_dir']}")
    
    times = result['times']
    files = result['files']
    
    print(f"\n⏱️ 处理耗时:")
    if times['sentence'] > 0:
        print(f"  句子拆分: {times['sentence']:.2f}秒")
    if times['audio'] > 0:
        print(f"  音频生成: {times['audio']:.2f}秒")
    if times['analysis'] > 0:
        print(f"  语言学分析: {times['analysis']:.2f}秒")
    if times['compression'] > 0:
        print(f"  音频压缩: {times['compression']:.2f}秒")
    if times['vocabulary'] > 0:
        print(f"  词汇处理: {times['vocabulary']:.2f}秒")
    print(f"  总耗时: {times['file_total']:.2f}秒")
    
    print(f"\n📁 生成文件:")
    if files['sentence_files'] > 0:
        print(f"  句子文件: {files['sentence_files']} 个")
    if files['audio_files'] > 0:
        print(f"  音频文件: {files['audio_files']} 个")
    if files['subtitle_files'] > 0:
        print(f"  字幕文件: {files['subtitle_files']} 个")
    if files['compressed_files'] > 0:
        print(f"  压缩文件: {files['compressed_files']} 个")
    if files['analyzed_files'] > 0:
        print(f"  分析文件: {files['analyzed_files']} 个")
    if files['chapter_vocab_files'] > 0:
        print(f"  词汇文件: {files['chapter_vocab_files']} 个")


def print_book_results(results: list[dict], args, program_start_time: float):
    """专门为书籍处理结果输出"""
    if not results:
        return
    
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
            'analysis': sum(r['times']['analysis'] for r in successful_results),
            'compression': sum(r['times']['compression'] for r in successful_results),
            'vocabulary': sum(r['times']['vocabulary'] for r in successful_results),
            'statistics': sum(r['times']['statistics'] for r in successful_results),
            'total': sum(r['times']['total'] for r in successful_results)
        }
        
        # 打印批量处理汇总
        print(f"\n📊 批量处理汇总 ({len(successful_results)}/{len(results)} 成功):")
        if args.chapter and total_times['total'] > 0:
            print(f"  章节拆分: {total_times['chapter']:.2f}秒 ({total_times['chapter']/total_times['total']*100:.1f}%)")
        if args.sentence and total_times['total'] > 0:
            print(f"  句子拆分: {total_times['sentence']:.2f}秒 ({total_times['sentence']/total_times['total']*100:.1f}%)")
        if args.audio and total_times['total'] > 0:
            print(f"  音频生成: {total_times['audio']:.2f}秒 ({total_times['audio']/total_times['total']*100:.1f}%)")
        if args.analysis and total_times['total'] > 0:
            print(f"  语言学分析: {total_times['analysis']:.2f}秒 ({total_times['analysis']/total_times['total']*100:.1f}%)")
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
                'analyzed_files': sum(r['files']['analyzed_files'] for r in successful_results),
                'chapter_vocab_files': sum(r['files']['chapter_vocab_files'] for r in successful_results)
            }
            
            print(f"\n📁 生成文件统计:")
            print(f"  生成的句子文件: {total_files['sentence_files']} 个")
            if args.audio and total_files['audio_files'] > 0:
                print(f"  生成的音频文件: {total_files['audio_files']} 个")
                print(f"  生成的字幕文件: {total_files['subtitle_files']} 个")
            if args.compress and total_files['compressed_files'] > 0:
                print(f"  压缩的音频文件: {total_files['compressed_files']} 个")
            if args.analysis and total_files['analyzed_files'] > 0:
                print(f"  分析的字幕文件: {total_files['analyzed_files']} 个")
            if args.vocabulary and total_files['chapter_vocab_files'] > 0:
                print(f"  生成的章节词汇文件: {total_files['chapter_vocab_files']} 个")
    
    # 显示失败的文件
    if failed_results:
        print(f"\n❌ 失败的文件 ({len(failed_results)} 个):")
        for result in failed_results:
            print(f"  • {os.path.basename(result['input_file'])}: {result['error']}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='章节拆分工具 - 将书籍文本拆分为独立的章节文件',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 书籍处理模式（完整流程）
  %(prog)s data/greens.txt --chapter --sentence --audio
  %(prog)s data/books/  # 批量处理目录下所有.txt文件
  %(prog)s data/book.txt --chapter --sentence --audio --analysis --vocabulary
  %(prog)s data/book.txt --sentence --audio  # 只运行句子拆分和音频生成
  %(prog)s data/book.txt --chapter  # 只运行章节拆分
  
  # 子章节处理模式（从句子拆分开始）
  %(prog)s output/book_name/sub_chapters/chapter_01_001.txt --sub-chapter --sentence --audio
  %(prog)s output/book_name/sub_chapters/chapter_01_001.txt --sub-chapter --sentence --audio --analysis
  %(prog)s output/book_name/sub_chapters/chapter_01_001.txt --sub-chapter --overwrite --sentence --audio  # 覆盖模式
  
默认配置文件: text_to_audiobook/config.json
默认输出目录: ./output
默认总词汇表: script/text_to_audiobook/vocabulary/master_vocabulary.json
输出格式: chapters/, sub_chapters/, sentences/, audio/, subtitles/, vocabulary/ 目录
        """
    )
    
    # 核心参数
    parser.add_argument('input_path',help='输入文本文件、目录路径或子章节文件路径')
    parser.add_argument('--verbose','-v',action='store_true',help='显示详细信息')
    
    # 处理模式参数
    parser.add_argument('--sub-chapter', action='store_true', help='处理单个子章节文件（从句子拆分开始）')
    parser.add_argument('--overwrite', action='store_true', help='覆盖模式：删除子章节对应的相关文件后重新处理')
    
    # 文本拆分参数
    parser.add_argument('--chapter', action='store_true', help='启用章节和子章节拆分')
    parser.add_argument('--sentence', action='store_true', help='启用句子拆分')

    # 音频生成参数
    parser.add_argument('--audio', action='store_true', help='启用音频生成')
    parser.add_argument('--voice', default='af_bella', help='语音模型 (默认: af_bella)')
    parser.add_argument('--speed', type=float, default=0.8, help='语音速度 (默认: 1.0)')
    
    # 翻译和分析参数
    parser.add_argument('--analysis', action='store_true', help='启用语言学分析')
    
    # 音频压缩参数
    parser.add_argument('--compress', action='store_true', help='启用音频压缩')
    
    # 词汇处理参数
    parser.add_argument('--vocabulary', action='store_true', help='启用词汇提取和分级')
    
    # 统计参数
    parser.add_argument('--stats', action='store_true', help='启用统计信息收集')
    args = parser.parse_args()

    # 配置路径
    config_path = os.path.join(os.path.dirname(__file__), 'config.json')

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
        
        # 根据处理模式分发
        if args.sub_chapter:
            # 单个子章节处理模式
            if not os.path.isfile(args.input_path):
                print("❌ 错误: 子章节模式需要指定单个文件")
                return 1
                
            # 验证文件是否在sub_chapters目录中
            if 'sub_chapters' not in args.input_path:
                print("❌ 错误: 文件不在sub_chapters目录中")
                return 1
                
            print(f"🔄 子章节处理模式")
            print(f"📁 处理文件: {os.path.basename(args.input_path)}")
            
            # 处理单个子章节
            try:
                result = process_single_sub_chapter(args.input_path, args, config, workflow)
                if result['success']:
                    print(f"✅ 子章节处理完成: {result['base_name']} ({result['times']['file_total']:.2f}秒)")
                    print_sub_chapter_results([result])
                else:
                    print(f"❌ 子章节处理失败: {result['error']}")
                    return 1
                    
            except Exception as e:
                print(f"❌ 子章节处理异常: {e}")
                if args.verbose:
                    import traceback
                    traceback.print_exc()
                return 1
                
        else:
            # 原有的书籍处理模式
            # 发现待处理的文件
            try:
                input_files = find_txt_files(args.input_path)
            except ValueError as e:
                print(f"❌ 错误: {e}")
                return 1
            
            # 显示发现的文件
            print(f"🔍 发现 {len(input_files)} 个 .txt 文件:")
            for i, file in enumerate(input_files, 1):
                print(f"  {i}. {os.path.basename(file)}")
            
            # 批量处理文件
            results = []
            for i, input_file in enumerate(input_files, 1):
                print(f"\n🚀 [{i}/{len(input_files)}] 开始处理: {os.path.basename(input_file)}")
                
                try:
                    result = process_single_book(input_file, args, config, workflow)
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
            
            # 显示书籍处理结果
            print_book_results(results, args, program_start_time)
        
        # 返回状态码 
        return 0
        
    except Exception as e:
        print(f"❌ 批量处理失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())