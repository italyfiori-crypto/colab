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

# Kokoro 相关导入 (用于句子音频)
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
        
        # 初始化Kokoro管道 (用于句子音频)
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
        
        # 为每个句子单独生成音频并获取真实时长
        temp_audio_files, durations = self._generate_individual_audios(sentences, base_name, audio_dir)
        
        if temp_audio_files and durations:
            # 将单句音频合并为完整音频文件
            if self._merge_audio_files(temp_audio_files, audio_file):
                # 使用真实时长生成精确字幕文件
                self._generate_subtitle_file(sentences, durations, subtitle_file)
                return audio_file, subtitle_file
            else:
                print(f"❌ 音频合并失败: {base_name}")
                return None, None
        else:
            print(f"❌ 单句音频生成失败: {base_name}")
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
            generator = self.tts_pipeline(text, voice=self.config.voice, speed=self.config.speed)
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
    
    def _generate_individual_audios(self, sentences: List[str], base_name: str, audio_dir: str) -> Tuple[List[str], List[float]]:
        """
        为每个句子单独生成音频文件
        
        Args:
            sentences: 句子列表
            base_name: 基础文件名
            audio_dir: 音频输出目录
            
        Returns:
            (音频文件列表, 对应的时长列表)
        """
        audio_files = []
        durations = []
        
        for i, sentence in enumerate(sentences):
            # 生成临时音频文件名
            temp_audio_file = os.path.join(audio_dir, f"{base_name}_temp_{i:03d}.{self.config.audio_format}")
            
            try:
                # 生成单句音频
                if self._generate_sentence_audio(sentence, temp_audio_file):
                    # 获取实际时长
                    duration = self._get_audio_duration(temp_audio_file)
                    if duration > 0:
                        audio_files.append(temp_audio_file)
                        durations.append(duration)
                    else:
                        print(f"⚠️ 句子音频时长为0: {sentence[:30]}...")
                        # 如果获取时长失败，删除临时文件
                        if os.path.exists(temp_audio_file):
                            os.remove(temp_audio_file)
                else:
                    print(f"⚠️ 句子音频生成失败: {sentence[:30]}...")
                    
            except Exception as e:
                print(f"❌ 处理句子失败 [{i}]: {e}")
                # 清理可能创建的临时文件
                if os.path.exists(temp_audio_file):
                    os.remove(temp_audio_file)
                continue
        
        return audio_files, durations
    
    def _merge_audio_files(self, audio_files: List[str], output_path: str) -> bool:
        """
        将多个音频文件合并为一个完整的音频文件
        
        Args:
            audio_files: 要合并的音频文件列表
            output_path: 输出音频文件路径
            
        Returns:
            合并是否成功
        """
        if not audio_files:
            return False
        
        try:
            # 读取所有音频文件
            audio_chunks = []
            for audio_file in audio_files:
                audio_data, sample_rate = sf.read(audio_file)
                # 确保采样率一致
                if sample_rate != self.config.sample_rate:
                    print(f"⚠️ 采样率不匹配: {audio_file} ({sample_rate} vs {self.config.sample_rate})")
                audio_chunks.append(audio_data)
            
            # 合并音频数据
            if audio_chunks:
                merged_audio = np.concatenate(audio_chunks)
                sf.write(output_path, merged_audio, self.config.sample_rate)
                
                # 清理临时文件
                for temp_file in audio_files:
                    try:
                        os.remove(temp_file)
                    except Exception as e:
                        print(f"⚠️ 清理临时文件失败: {e}")
                
                return True
            else:
                return False
                
        except Exception as e:
            print(f"❌ 音频合并失败: {e}")
            return False
    
    def _generate_subtitle_file(self, sentences: List[str], durations: List[float], output_path: str):
        """
        生成字幕文件（SRT格式）
        
        Args:
            sentences: 句子列表
            durations: 每个句子对应的真实时长列表
            output_path: 输出字幕文件路径
        """
        if not sentences or not durations:
            return
        
        # 确保句子和时长列表长度匹配
        if len(sentences) != len(durations):
            print(f"⚠️ 句子数量({len(sentences)})与时长数量({len(durations)})不匹配")
            return
        
        srt_content = []
        current_time = 0.0
        
        for i, (sentence, duration) in enumerate(zip(sentences, durations), 1):
            start_time = current_time
            end_time = current_time + duration
            
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
    
