#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本转有声书脚本 - 重构版
将古腾堡项目的文本文件转换为带字幕的有声书

使用方法:
python script/text_to_audiobook.py data/alice.txt

依赖:
pip install kokoro torch torchaudio soundfile spacy
python -m spacy download en_core_web_sm
"""

import os
import sys
import argparse
from pathlib import Path

# 添加modules目录到Python路径
script_dir = Path(__file__).parent
modules_dir = script_dir / "modules"
sys.path.insert(0, str(modules_dir))

try:
    from modules import TextProcessor, TextSplitter, AudioGenerator, SubtitleGenerator, StatisticsCollector, ChineseTranslator
except ImportError as e:
    print(f"导入模块失败: {e}")
    print("请确保所有模块文件都在modules目录中")
    sys.exit(1)


class TextToAudiobook:
    """文本转有声书转换器"""
    
    def __init__(self, input_file: str, output_dir: str = "output", force_rebuild: bool = False):
        """
        初始化转换器
        
        Args:
            input_file: 输入文本文件路径
            output_dir: 输出目录路径
            force_rebuild: 是否强制重新构建所有章节（跳过已处理检查）
        """
        self.input_file = Path(input_file)
        self.output_dir = Path(output_dir)
        self.audio_dir = self.output_dir / "audio"
        self.subtitle_dir = self.output_dir / "subtitles"
        self.force_rebuild = force_rebuild
        
        # 确保输出目录存在
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.subtitle_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化各个模块
        self.text_processor = TextProcessor()
        self.text_splitter = TextSplitter()
        self.audio_generator = AudioGenerator(voice='af_heart')
        self.subtitle_generator = SubtitleGenerator()
        self.statistics = StatisticsCollector()
        
        # 初始化翻译器（必需功能）
        self.translator = ChineseTranslator()
        # 测试API连接 - 失败直接退出
        if not self.translator.test_connection():
            print("❌ 翻译功能初始化失败，程序退出")
            sys.exit(1)
    
    def _is_chapter_processed(self, chapter_name: str) -> bool:
        """
        检查章节是否已经处理完成
        
        Args:
            chapter_name: 章节名称（如chapter_01）
            
        Returns:
            章节是否已处理完成
        """
        if self.force_rebuild:
            return False
            
        audio_file = self.audio_dir / f"{chapter_name}.wav"
        subtitle_file = self.subtitle_dir / f"{chapter_name}.srt"
        
        # 检查文件是否存在且大小合理
        if not (audio_file.exists() and subtitle_file.exists()):
            return False
        
        # 检查文件大小（避免空文件或损坏文件）
        if audio_file.stat().st_size < 1000 or subtitle_file.stat().st_size < 100:
            return False
        
        return True
    
    def convert(self):
        """执行完整的转换过程"""
        print(f"开始转换文件: {self.input_file}")
        
        # 读取输入文件 - 失败直接退出
        with open(self.input_file, 'r', encoding='utf-8') as f:
            text = f.read()
        
        # 提取书籍信息
        print("正在提取书籍信息...")
        book_info = self.text_processor.extract_book_info(text)
        book_title_en = book_info.get('title', self.input_file.stem.replace('_', ' ').title())
        author = book_info.get('author', '')
        
        print(f"📖 书名: {book_title_en}")
        if author:
            print(f"✍️  作者: {author}")
        
        # 翻译书名
        print("正在翻译书名...")
        book_title_zh = self.translator.translate_book_title(book_title_en) if book_title_en else ""
        if book_title_zh:
            print(f"📖 中文书名: {book_title_zh}")
        
        # 预处理文本
        print("正在预处理文本...")
        chapters = self.text_processor.preprocess_text(text)
        print(f"识别到 {len(chapters)} 个章节")
        
        # 重新初始化统计收集器，包含双语书名信息
        self.statistics = StatisticsCollector(book_title_en, book_title_zh, author)
        
        # 转换每个章节
        total_duration = 0
        processed_count = 0
        skipped_count = 0
        
        for i, chapter in enumerate(chapters, 1):
            chapter_name = f"chapter_{i:02d}"
            audio_file = self.audio_dir / f"{chapter_name}.wav"
            temp_subtitle_file = self.subtitle_dir / f"{chapter_name}_temp.srt"  # 临时英文字幕
            final_subtitle_file = self.subtitle_dir / f"{chapter_name}.srt"      # 最终合并字幕
            
            chapter_title_en = chapter['title']
            
            # 检查章节是否已经处理完成
            if self._is_chapter_processed(chapter_name):
                print(f"\\n跳过章节 {i}/{len(chapters)}: {chapter_title_en} (已处理)")
                skipped_count += 1
                
                # 获取已处理章节的时长（用于统计）
                try:
                    import wave
                    with wave.open(str(audio_file), 'rb') as wav_file:
                        frames = wav_file.getnframes()
                        rate = wav_file.getframerate()
                        duration = frames / float(rate)
                        total_duration += duration
                except:
                    # 如果无法读取音频文件，跳过时长统计
                    pass
                continue
            
            print(f"\\n处理章节 {i}/{len(chapters)}: {chapter_title_en}")
            processed_count += 1
            
            # 翻译章节标题
            print(f"  正在翻译章节标题...")
            chapter_title_zh = self.translator.translate_chapter_title(chapter_title_en)
            if chapter_title_zh:
                print(f"  中文标题: {chapter_title_zh}")
            
            # 过滤内容：移除章节标题和描述
            content = self.text_processor.filter_chapter_titles(
                chapter['content'], chapter_title_en
            )
            
            if not content.strip():
                print("❌ 章节内容为空，处理失败")
                sys.exit(1)
            
            # 一次性分割文本（统一使用120字符）
            print(f"  正在分割文本（最大120字符/段）...")
            segments = self.text_splitter.split_text(content, max_length=120)
            print(f"  分割完成：{len(segments)} 个文本段")
            
            # 生成音频（使用预分割的文本段）
            audio_result = self.audio_generator.generate_audio_from_segments(
                segments, audio_file
            )
            
            duration = audio_result.get("duration", 0)
            segments_count = audio_result.get("segments_count", 0)
            segment_timings = audio_result.get("segment_timings", [])
            
            if duration > 0:
                # 生成临时英文字幕（使用预分割的文本段和音频时间信息）
                # 每个章节独立时间轴，从00:00:00开始
                subtitle_count = self.subtitle_generator.generate_subtitle_from_segments(
                    segments, segment_timings, temp_subtitle_file, chapter_offset=0.0
                )
                
                # 生成中英文合并字幕 - 翻译器必须可用
                print(f"  正在生成中英文合并字幕...")
                if not self.translator.generate_bilingual_subtitle(temp_subtitle_file, final_subtitle_file):
                    print("❌ 字幕翻译失败，程序退出")
                    sys.exit(1)
                # 删除临时文件
                temp_subtitle_file.unlink(missing_ok=True)
                
                # 收集章节统计信息
                self.statistics.add_chapter_stats(
                    chapter_number=i,
                    chapter_title_en=chapter_title_en,
                    chapter_title_zh=chapter_title_zh,
                    text=content,
                    subtitle_count=subtitle_count,
                    segments_count=segments_count,
                    audio_duration=duration
                )
                
                total_duration += duration
        
        # 导出统计信息
        print("\\n正在生成统计报告...")
        metadata_file = self.output_dir / "metadata.json"
        readme_file = self.output_dir / "README.md"
        
        self.statistics.export_json(metadata_file)
        self.statistics.export_markdown(readme_file)
        
        # 打印统计摘要
        self.statistics.print_summary()
        
        print(f"\\n✅ 转换完成！")
        print(f"📊 处理统计: 新处理 {processed_count} 个章节, 跳过 {skipped_count} 个已处理章节")
        print(f"📁 音频文件: {self.audio_dir}")
        print(f"📁 字幕文件: {self.subtitle_dir}")
        print(f"📊 统计信息: {metadata_file}")
        print(f"📖 详细报告: {readme_file}")
        
        if processed_count == 0 and skipped_count > 0:
            print("\\n💡 所有章节已处理完成。如需重新处理，请使用 --force-rebuild 参数")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="将文本文件转换为有声书（包含中文翻译）")
    parser.add_argument("input_file", help="输入文本文件路径")
    parser.add_argument("-o", "--output", default="test_output", help="输出目录 (默认: test_output)")
    parser.add_argument("--force-rebuild", action="store_true", 
                       help="强制重新处理所有章节（跳过已处理检查）")
    
    args = parser.parse_args()
    
    # 检查输入文件是否存在
    if not os.path.exists(args.input_file):
        print(f"错误: 输入文件不存在: {args.input_file}")
        sys.exit(1)
    
    # 显示处理模式
    if args.force_rebuild:
        print("🔄 强制重建模式: 将重新处理所有章节")
    else:
        print("⚡ 增量处理模式: 将跳过已处理章节")
    
    # 创建转换器并执行转换
    converter = TextToAudiobook(args.input_file, args.output, args.force_rebuild)
    converter.convert()


if __name__ == "__main__":
    main()