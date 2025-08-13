#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本转有声书脚本
将古腾堡项目的文本文件转换为带字幕的有声书

使用方法:
python script/text_to_audiobook.py data/alice.txt

依赖:
pip install kokoro torch torchaudio soundfile
"""

import os
import sys
import re
import argparse
import time
from pathlib import Path
from datetime import timedelta
from typing import List, Tuple, Dict

try:
    import torch
    import soundfile as sf
    import numpy as np
    # Kokoro库的正确导入方式
    from kokoro import KPipeline
except ImportError as e:
    print(f"缺少依赖包: {e}")
    print("请安装必要依赖: pip install kokoro>=0.9.4 soundfile")
    print("Linux/Ubuntu用户还需要: apt-get install espeak-ng")
    sys.exit(1)


class TextToAudiobook:
    def __init__(self, input_file: str, output_dir: str = "output"):
        """
        初始化转换器
        
        Args:
            input_file: 输入文本文件路径
            output_dir: 输出目录路径
        """
        self.input_file = Path(input_file)
        self.output_dir = Path(output_dir)
        self.audio_dir = self.output_dir / "audio"
        self.subtitle_dir = self.output_dir / "subtitles"
        
        # 确保输出目录存在
        self.audio_dir.mkdir(parents=True, exist_ok=True)
        self.subtitle_dir.mkdir(parents=True, exist_ok=True)
        
        # 语音合成参数
        self.sample_rate = 24000
        self.words_per_minute = 150  # 估算语速，用于字幕时间计算
        
        # 初始化Kokoro管道
        self.simulate_mode = False
        try:
            # 使用美式英语，你可以根据需要修改语言代码
            self.tts_pipeline = KPipeline(lang_code='a')  # 'a' for American English
            self.voice = 'af_nicole'  # 默认声音，可以根据需要修改
            print("Kokoro TTS管道加载成功")
        except Exception as e:
            print(f"Kokoro TTS管道加载失败: {e}")
            print("将使用模拟模式（仅生成字幕文件）")
            self.tts_pipeline = None
            self.simulate_mode = True
        
    def preprocess_text(self, text: str) -> List[Dict[str, str]]:
        """
        预处理文本：删除头部信息、目录，按章节分割
        
        Args:
            text: 原始文本内容
            
        Returns:
            章节列表，每个元素包含 {'title': str, 'content': str}
        """
        lines = text.split('\n')
        
        # 删除古腾堡项目头部信息
        content_start = 0
        for i, line in enumerate(lines):
            if "CHAPTER I" in line.upper() or "第一章" in line or line.strip().startswith("1."):
                content_start = i
                break
        
        # 如果没有找到明确的开始标记，尝试删除前30行的标准头部
        if content_start == 0:
            for i, line in enumerate(lines[:50]):
                if line.strip() and not any(marker in line.upper() for marker in 
                    ["PROJECT GUTENBERG", "START OF", "CONTENTS", "目录", "ILLUSTRATION", "***"]):
                    content_start = i
                    break
        
        content_lines = lines[content_start:]
        
        # 按章节分割
        chapters = []
        current_chapter = {"title": "开始", "content": ""}
        
        for line in content_lines:
            line = line.strip()
            
            # 识别章节标题
            if self._is_chapter_title(line):
                # 保存上一章节
                if current_chapter["content"].strip():
                    chapters.append(current_chapter)
                
                # 开始新章节
                current_chapter = {
                    "title": line,
                    "content": ""
                }
            else:
                # 添加到当前章节内容
                if line:
                    current_chapter["content"] += line + " "
        
        # 添加最后一个章节
        if current_chapter["content"].strip():
            chapters.append(current_chapter)
        
        # 清理章节内容
        for chapter in chapters:
            chapter["content"] = self._clean_content(chapter["content"])
        
        return chapters
    
    def _is_chapter_title(self, line: str) -> bool:
        """判断是否为章节标题"""
        line_upper = line.upper()
        patterns = [
            r'CHAPTER\s+[IVX\d]+',
            r'第.+章',
            r'PART\s+[IVX\d]+',
            r'^\d+\.',
            r'BOOK\s+[IVX\d]+'
        ]
        
        return any(re.match(pattern, line_upper) for pattern in patterns)
    
    def _clean_content(self, content: str) -> str:
        """清理文本内容"""
        # 删除多余空白
        content = re.sub(r'\s+', ' ', content)
        
        # 删除格式标记
        content = re.sub(r'\[Illustration.*?\]', '', content)
        content = re.sub(r'\*{3,}.*?\*{3,}', '', content)
        
        # 规范化标点符号
        content = content.replace('"', '"').replace('"', '"')
        content = content.replace(''', "'").replace(''', "'")
        
        return content.strip()
    
    def _split_text_to_segments(self, text: str, max_length: int = 100) -> List[str]:
        """
        将文本分割成适合语音合成的小段，支持多级分割
        
        Args:
            text: 要分割的文本
            max_length: 每段的最大长度
            
        Returns:
            分割后的文本段列表
        """
        # 首先按句子分割
        sentences = self._split_sentences(text)
        
        segments = []
        current_segment = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # 检查单个句子是否过长，如需要进一步分割
            if len(sentence) > max_length:
                # 如果当前段不为空，先保存
                if current_segment:
                    segments.append(current_segment)
                    current_segment = ""
                
                # 对长句子按标点符号进一步分割
                sub_segments = self._split_long_sentence(sentence, max_length)
                segments.extend(sub_segments)
            else:
                # 如果当前段加上新句子不会超过最大长度
                if len(current_segment) + len(sentence) + 2 <= max_length:
                    if current_segment:
                        current_segment += ". " + sentence
                    else:
                        current_segment = sentence
                else:
                    # 保存当前段并开始新段
                    if current_segment:
                        segments.append(current_segment)
                    current_segment = sentence
        
        # 添加最后一段
        if current_segment:
            segments.append(current_segment)
        
        return segments
    
    def _split_long_sentence(self, sentence: str, max_length: int) -> List[str]:
        """
        对过长的句子按标点符号进一步分割
        
        Args:
            sentence: 要分割的长句子
            max_length: 每段的最大长度
            
        Returns:
            分割后的子段列表
        """
        # 按常见的句内分隔符分割
        delimiters = [';', ':', ',', '--', '—', '(', ')', '[', ']']
        
        segments = [sentence]
        
        for delimiter in delimiters:
            new_segments = []
            for seg in segments:
                if len(seg) > max_length and delimiter in seg:
                    parts = seg.split(delimiter)
                    current = ""
                    for i, part in enumerate(parts):
                        part = part.strip()
                        if not part:
                            continue
                        
                        # 重新加上分隔符（除了最后一部分）
                        if i < len(parts) - 1:
                            part += delimiter
                        
                        if len(current) + len(part) + 1 <= max_length:
                            if current:
                                current += " " + part
                            else:
                                current = part
                        else:
                            if current:
                                new_segments.append(current)
                            current = part
                    
                    if current:
                        new_segments.append(current)
                else:
                    new_segments.append(seg)
            segments = new_segments
        
        # 如果还是太长，按空格强制分割
        final_segments = []
        for seg in segments:
            if len(seg) <= max_length:
                final_segments.append(seg)
            else:
                # 按空格分割
                words = seg.split()
                current = ""
                for word in words:
                    if len(current) + len(word) + 1 <= max_length:
                        if current:
                            current += " " + word
                        else:
                            current = word
                    else:
                        if current:
                            final_segments.append(current)
                        current = word
                
                if current:
                    final_segments.append(current)
        
        return final_segments
    
    def generate_audio(self, text: str, output_path: Path) -> float:
        """
        生成音频文件
        
        Args:
            text: 要转换的文本
            output_path: 输出音频文件路径
            
        Returns:
            音频时长（秒）
        """
        if self.tts_pipeline is None or self.simulate_mode:
            print("使用模拟模式生成音频时长估算")
            # 根据文本长度估算音频时长（按平均语速150词/分钟）
            word_count = len(text.split())
            estimated_duration = (word_count / self.words_per_minute) * 60
            print(f"估算音频时长: {estimated_duration:.2f}秒")
            return estimated_duration
            
        try:
            print(f"正在生成音频: {output_path.name}")
            print(f"文本长度: {len(text)} 字符")
            
            # 分段处理长文本（每段最多300字符，避免过长的句子）
            segments = self._split_text_to_segments(text, max_length=300)
            
            # 生成各段的音频
            all_audio = []
            for i, segment in enumerate(segments):
                if segment.strip():
                    print(f"  处理第 {i+1}/{len(segments)} 段...")
                    try:
                        # 使用Kokoro生成语音
                        generator = self.tts_pipeline(segment, voice=self.voice)
                        segment_audio = []
                        
                        for j, (graphemes, phonemes, audio_chunk) in enumerate(generator):
                            if isinstance(audio_chunk, torch.Tensor):
                                audio_chunk = audio_chunk.cpu().numpy()
                            segment_audio.append(audio_chunk)
                        
                        if segment_audio:
                            combined_segment = np.concatenate(segment_audio)
                            all_audio.append(combined_segment)
                        
                    except Exception as e:
                        print(f"  段 {i+1} 生成失败: {e}")
                        continue
            
            if not all_audio:
                print("没有成功生成任何音频段")
                return 0.0
            
            # 合并所有音频段
            audio = np.concatenate(all_audio)
            
            # 保存音频文件
            sf.write(str(output_path), audio, self.sample_rate)
            
            # 计算音频时长
            duration = len(audio) / self.sample_rate
            
            print(f"音频生成完成，时长: {duration:.2f}秒")
            return duration
            
        except Exception as e:
            print(f"生成音频时出错: {e}")
            return 0.0
    
    def generate_subtitle(self, text: str, duration: float, output_path: Path, chapter_offset: float = 0):
        """
        生成SRT字幕文件
        
        Args:
            text: 文本内容
            duration: 音频时长
            output_path: 输出字幕文件路径
            chapter_offset: 章节时间偏移（用于合并字幕）
        """
        print(f"正在生成字幕: {output_path.name}")
        
        # 使用改进的段落分割方法，生成短字幕条目 
        segments = self._split_text_to_segments(text, max_length=120)  # 字幕行更短一些
        
        if not segments:
            return
        
        # 计算每段的时间分配
        subtitle_entries = []
        total_chars = sum(len(s) for s in segments)
        current_time = chapter_offset
        
        for i, segment in enumerate(segments):
            segment = segment.strip()
            if not segment:
                continue
            
            # 根据字符数估算时长
            segment_duration = (len(segment) / total_chars) * duration
            start_time = current_time
            end_time = current_time + segment_duration
            
            # 格式化时间戳
            start_timestamp = self._format_timestamp(start_time)
            end_timestamp = self._format_timestamp(end_time)
            
            subtitle_entries.append({
                'index': len(subtitle_entries) + 1,
                'start': start_timestamp,
                'end': end_timestamp,
                'text': segment
            })
            
            current_time = end_time
        
        # 写入SRT文件
        with open(output_path, 'w', encoding='utf-8') as f:
            for entry in subtitle_entries:
                f.write(f"{entry['index']}\n")
                f.write(f"{entry['start']} --> {entry['end']}\n")
                f.write(f"{entry['text']}\n\n")
        
        print(f"字幕生成完成，共 {len(subtitle_entries)} 条字幕")
    
    def _split_sentences(self, text: str) -> List[str]:
        """按句子分割文本"""
        # 使用正则表达式分割句子
        sentences = re.split(r'[.!?。！？]+\s*', text)
        
        # 清理空句子
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _format_timestamp(self, seconds: float) -> str:
        """格式化时间戳为SRT格式"""
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        seconds = td.total_seconds() % 60
        milliseconds = int((seconds % 1) * 1000)
        seconds = int(seconds)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    
    def convert(self):
        """执行完整的转换过程"""
        print(f"开始转换文件: {self.input_file}")
        
        # 读取输入文件
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                text = f.read()
        except Exception as e:
            print(f"读取文件失败: {e}")
            return
        
        # 预处理文本
        print("正在预处理文本...")
        chapters = self.preprocess_text(text)
        print(f"识别到 {len(chapters)} 个章节")
        
        # 转换每个章节
        total_duration = 0
        
        for i, chapter in enumerate(chapters, 1):
            chapter_name = f"chapter_{i:02d}"
            audio_file = self.audio_dir / f"{chapter_name}.wav"
            subtitle_file = self.subtitle_dir / f"{chapter_name}.srt"
            
            print(f"\n处理章节 {i}/{len(chapters)}: {chapter['title']}")
            
            # 过滤内容：移除章节标题
            content = chapter['content']
            
            # 如果内容以章节标题开头，去除它
            if self._is_chapter_title(chapter['title']):
                # 从内容中移除可能重复的章节标题
                lines = content.split('\n')
                filtered_lines = []
                for line in lines:
                    line = line.strip()
                    if line and not self._is_chapter_title(line):
                        filtered_lines.append(line)
                content = ' '.join(filtered_lines)
            
            if not content.strip():
                print("  章节内容为空，跳过")
                continue
            
            # 生成音频
            duration = self.generate_audio(content, audio_file)
            if duration > 0:
                # 生成字幕
                self.generate_subtitle(content, duration, subtitle_file, total_duration)
                total_duration += duration
            
        print(f"\n转换完成！")
        print(f"总时长: {total_duration/60:.2f} 分钟")
        print(f"音频文件保存在: {self.audio_dir}")
        print(f"字幕文件保存在: {self.subtitle_dir}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="将文本文件转换为有声书")
    parser.add_argument("input_file", help="输入文本文件路径")
    parser.add_argument("-o", "--output", default="output", help="输出目录 (默认: output)")
    
    args = parser.parse_args()
    
    # 检查输入文件是否存在
    if not os.path.exists(args.input_file):
        print(f"错误: 输入文件不存在: {args.input_file}")
        sys.exit(1)
    
    # 创建转换器并执行转换
    converter = TextToAudiobook(args.input_file, args.output)
    converter.convert()


if __name__ == "__main__":
    main()