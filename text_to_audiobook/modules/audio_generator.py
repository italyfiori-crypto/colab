#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频生成模块
使用 Kokoro TTS 将句子文件转换为语音和字幕
"""

import os
import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

# Kokoro 相关导入
import torch
import soundfile as sf
from kokoro import KPipeline


@dataclass
class AudioGeneratorConfig:
    """音频生成配置"""
    
    # 输出目录配置
    audio_subdir: str = "audio"
    subtitle_subdir: str = "subtitles"
    
    # Kokoro 模型配置
    voice: str = "af_bella"  # 默认声音
    speed: float = 1.0
    
    # 输出格式配置
    sample_rate: int = 24000
    audio_format: str = "wav"
    subtitle_format: str = "srt"


class AudioGenerator:
    """音频生成器 - 处理句子文件生成音频和字幕"""
    
    def __init__(self, config: AudioGeneratorConfig):
        """
        初始化音频生成器
        
        Args:
            config: 音频生成配置
        """
        self.config = config
        self.words_per_minute = 150  # 估算语速
        
        # 初始化Kokoro管道
        try:
            self.tts_pipeline = KPipeline(lang_code='a')  # 'a' for American English
            print("Kokoro TTS管道加载成功")
        except Exception as e:
            raise RuntimeError(f"Kokoro TTS管道初始化失败: {e}")
    
    def generate_audio_files(self, sentence_files: List[str], output_dir: str) -> Tuple[List[str], List[str]]:
        """
        批量生成音频和字幕文件
        
        Args:
            sentence_files: 句子文件路径列表
            output_dir: 输出根目录
            
        Returns:
            (音频文件列表, 字幕文件列表)
        """
        # 创建输出目录
        audio_dir = os.path.join(output_dir, self.config.audio_subdir)
        subtitle_dir = os.path.join(output_dir, self.config.subtitle_subdir)
        os.makedirs(audio_dir, exist_ok=True)
        os.makedirs(subtitle_dir, exist_ok=True)
        
        audio_files = []
        subtitle_files = []
        
        for sentence_file in sentence_files:
            try:
                # 处理单个文件
                audio_file, subtitle_file = self._process_file(sentence_file, audio_dir, subtitle_dir)
                if audio_file:
                    audio_files.append(audio_file)
                if subtitle_file:
                    subtitle_files.append(subtitle_file)
                
                filename = os.path.basename(sentence_file)
                print(f"🔊 已处理音频生成: {filename}")
                
            except Exception as e:
                print(f"❌ 音频生成失败: {e}")
                continue
        
        print(f"\n🎵 音频生成完成，输出到: {audio_dir}")
        print(f"📄 字幕生成完成，输出到: {subtitle_dir}")
        return audio_files, subtitle_files
    
    def _process_file(self, sentence_file: str, audio_dir: str, subtitle_dir: str) -> Tuple[Optional[str], Optional[str]]:
        """
        处理单个句子文件，生成对应的音频和字幕
        
        Args:
            sentence_file: 句子文件路径
            audio_dir: 音频输出目录
            subtitle_dir: 字幕输出目录
            
        Returns:
            (音频文件路径, 字幕文件路径)
        """
        # 读取句子文件
        with open(sentence_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取标题和句子
        lines = content.split('\n')
        title = lines[0].strip() if lines else "Unknown"
        
        # 提取所有非空行作为句子
        sentences = []
        for line in lines[1:]:
            line = line.strip()
            if line and any(c.isalpha() for c in line):  # 忽略没有单词的句子
                sentences.append(line)
                
        if not sentences:
            print(f"⚠️ 文件无有效句子: {os.path.basename(sentence_file)}")
            return None, None
        
        # 生成文件名
        base_name = os.path.splitext(os.path.basename(sentence_file))[0]
        audio_file = os.path.join(audio_dir, f"{base_name}.{self.config.audio_format}")
        subtitle_file = os.path.join(subtitle_dir, f"{base_name}.{self.config.subtitle_format}")
        
        # 合并所有句子生成单个音频文件
        full_text = " ".join(sentences)
        if self._generate_sentence_audio(full_text, audio_file):
            # 生成字幕文件
            audio_duration = self._get_audio_duration(audio_file)
            self._generate_subtitle_file(sentences, audio_duration, subtitle_file)
            return audio_file, subtitle_file
        else:
            return None, None
    
    def _generate_sentence_audio(self, text: str, output_path: str) -> bool:
        """
        生成单个句子的音频
        
        Args:
            text: 要转换的文本
            output_path: 输出音频文件路径
            
        Returns:
            是否生成成功
        """
        try:
            # 使用Kokoro管道生成音频
            generator = self.tts_pipeline(text, voice=self.config.voice)
            audio_chunks = []
            
            for (_, _, audio_chunk) in generator:
                if isinstance(audio_chunk, torch.Tensor):
                    audio_chunk = audio_chunk.cpu().numpy()
                audio_chunks.append(audio_chunk)
            
            if not audio_chunks:
                print(f"❌ 音频生成失败: {text[:50]}...")
                return False
            
            # 合并音频块并保存
            audio = np.concatenate(audio_chunks)
            sf.write(output_path, audio, self.config.sample_rate)
            return True
                
        except Exception as e:
            print(f"❌ 音频生成异常: {e}")
            return False
    
    def _get_audio_duration(self, audio_path: str) -> float:
        """
        获取音频文件时长（秒）
        
        Args:
            audio_path: 音频文件路径
            
        Returns:
            音频时长（秒）
        """
        try:
            # 使用soundfile获取音频信息
            info = sf.info(audio_path)
            return info.duration
        except Exception as e:
            print(f"❌ 获取音频时长失败: {e}")
            return 0.0
    
    def _generate_subtitle_file(self, sentences: List[str], total_duration: float, output_path: str):
        """
        生成字幕文件（SRT格式）
        
        Args:
            sentences: 句子列表
            total_duration: 总音频时长
            output_path: 输出字幕文件路径
        """
        if not sentences:
            return
        
        # 计算每个句子的时长（简单平均分配）
        sentence_duration = total_duration / len(sentences)
        
        srt_content = []
        current_time = 0.0
        
        for i, sentence in enumerate(sentences, 1):
            start_time = current_time
            end_time = current_time + sentence_duration
            
            # 格式化时间戳
            start_timestamp = self._format_timestamp(start_time)
            end_timestamp = self._format_timestamp(end_time)
            
            # 添加字幕条目
            srt_content.append(f"{i}")
            srt_content.append(f"{start_timestamp} --> {end_timestamp}")
            srt_content.append(sentence)
            srt_content.append("")  # 空行分隔
            
            current_time = end_time
        
        # 写入文件
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(srt_content))
    
    def _format_timestamp(self, seconds: float) -> str:
        """
        格式化时间戳为 SRT 格式 (HH:MM:SS,mmm)
        
        Args:
            seconds: 秒数
            
        Returns:
            格式化的时间戳
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"