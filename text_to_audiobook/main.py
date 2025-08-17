@@ -1,214 +0,0 @@
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
from pathlib import Path

# 添加模块路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.chapter_splitter import ChapterSplitter
from modules.config import AudiobookConfig
from modules.sub_chapter_splitter import SubChapterSplitter
from modules.sentence_splitter import SentenceSplitter
from modules.audio_generator import AudioGenerator, AudioGeneratorConfig
from modules.subtitle_translator import SubtitleTranslator, SubtitleTranslatorConfig


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='章节拆分工具 - 将书籍文本拆分为独立的章节文件',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  %(prog)s data/greens.txt
  %(prog)s data/book.txt --output-dir ./my_output
  %(prog)s data/book.txt --audio --translate --api-key YOUR_API_KEY
  %(prog)s data/book.txt --config my_config.json --verbose
  
默认配置文件: text_to_audiobook/config.json
默认输出目录: ./output
输出格式: chapters/, sub_chapters/, sentences/, audio/, subtitles/ 目录
        """
    )
    
    # 核心参数
    parser.add_argument('input_file',help='输入文本文件路径')
    parser.add_argument('--output-dir', default='./output', help='输出目录路径 (默认: ./output)')
    parser.add_argument('--config', default='text_to_audiobook/config.json', help='配置文件路径 (默认: text_to_audiobook/config.json)')
    parser.add_argument('--verbose','-v',action='store_true',help='显示详细信息')
    
    # 音频生成参数
    parser.add_argument('--audio', action='store_true', help='启用音频生成')
    parser.add_argument('--voice', default='af_bella', help='语音模型 (默认: af_bella)')
    parser.add_argument('--speed', type=float, default=1.0, help='语音速度 (默认: 1.0)')
    
    # 字幕翻译参数
    parser.add_argument('--translate', action='store_true', help='启用字幕翻译')
    
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
        config_path = Path(args.config)
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
            start_time = time.time()
            try:
                audio_config = AudioGeneratorConfig(voice=args.voice, speed=args.speed)
                audio_generator = AudioGenerator(audio_config)
                audio_files, subtitle_files = audio_generator.generate_audio_files(sentence_files, output_dir)
                audio_time = time.time() - start_time
                
                print(f"\n✅ 音频生成完成! 生成 {len(audio_files)} 个音频文件和 {len(subtitle_files)} 个字幕文件 (耗时: {audio_time:.2f}秒)")
            except Exception as e:
                audio_time = time.time() - start_time
                print(f"\n⚠️ 音频生成失败: {e} (耗时: {audio_time:.2f}秒)")
                if args.verbose:
                    import traceback
                    traceback.print_exc()
                print("继续执行其他步骤...")
        
        # 执行字幕翻译（可选）
        translated_files = []
        translate_time = 0
        if args.translate and subtitle_files:
            print(f"\n🌏 开始字幕翻译处理...")
            start_time = time.time()
            try:
                # 配置翻译器
                translator_config = config.subtitle_translator                
                if not translator_config.api_key:
                    raise RuntimeError("缺少 SiliconFlow API 密钥，请通过 --api-key 参数或配置文件提供")
                
                translator = SubtitleTranslator(translator_config)
                translated_files = translator.translate_subtitle_files(subtitle_files)
                translate_time = time.time() - start_time
                
                print(f"\n✅ 字幕翻译完成! 翻译 {len(translated_files)} 个字幕文件 (耗时: {translate_time:.2f}秒)")
            except Exception as e:
                translate_time = time.time() - start_time
                print(f"\n⚠️ 字幕翻译失败: {e} (耗时: {translate_time:.2f}秒)")
                if args.verbose:
                    import traceback
                    traceback.print_exc()
                print("继续执行其他步骤...")
        elif args.translate and not subtitle_files:
            print(f"\n⚠️ 未找到字幕文件，跳过翻译步骤（请先启用 --audio 生成字幕）")
        
        # 计算总耗时
        total_time = chapter_time + sub_chapter_time + sentence_time + audio_time + translate_time
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
        
        return 0
        
    except Exception as e:
        print(f"❌ 拆分失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())