#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频生成模块
使用Kokoro TTS生成语音音频
"""

from pathlib import Path
from typing import Dict, List
import numpy as np

import torch
import soundfile as sf
from kokoro import KPipeline


class AudioGenerator:
    """音频生成器"""
    
    def __init__(self, voice, sample_rate: int = 24000):
        """
        初始化音频生成器
        
        Args:
            voice: 使用的声音模型
            sample_rate: 采样率
        """
        self.voice = voice
        self.sample_rate = sample_rate
        self.words_per_minute = 150  # 估算语速
        # 初始化Kokoro管道 - 必须成功
        self.tts_pipeline = KPipeline(lang_code='a')  # 'a' for American English
        print("Kokoro TTS管道加载成功")
    
    
    def generate_audio_from_segments(self, segments: List[str], output_path: Path) -> Dict:
        """
        从预分割的文本段生成音频文件
        
        Args:
            segments: 预分割的文本段列表
            output_path: 输出音频文件路径
            
        Returns:
            包含音频统计信息和分段时间信息的字典: {
                'duration': float,
                'segments_count': int,
                'segment_timings': [{'text': str, 'start_time': float, 'end_time': float, 'duration': float}]
            }
        """        
        try:
            print(f"正在生成音频: {output_path.name}")
            segments_count = len(segments)
            total_words = sum(len(seg.split()) for seg in segments)
            print(f"待处理：{segments_count} 个文本段，共 {total_words} 个单词")
            
            # 生成各段的音频并记录时间信息
            all_audio = []
            segment_timings = []
            current_time = 0.0
            
            for i, segment in enumerate(segments):
                if segment.strip():
                    print(f"  处理第 {i+1}/{segments_count} 段...")
                    
                    # 生成音频 - 必须成功
                    segment_audio = self._generate_segment_audio(segment)
                    # 计算当前段的时长
                    segment_duration = len(segment_audio) / self.sample_rate
                    all_audio.append(segment_audio)
                        
                    # 记录分段时间信息
                    segment_timings.append({
                        'text': segment.strip(),
                        'start_time': current_time,
                        'end_time': current_time + segment_duration,
                        'duration': segment_duration
                    })
                    
                    current_time += segment_duration
                    print(f"    段时长: {segment_duration:.3f}秒")
            
            # 合并所有音频段并保存
            audio = np.concatenate(all_audio)
            sf.write(str(output_path), audio, self.sample_rate)
            duration = len(audio) / self.sample_rate
            
            print(f"音频生成完成，时长: {duration:.2f}秒")
            print(f"共处理 {len(segment_timings)} 个文本段")
            return {
                "duration": duration, 
                "segments_count": segments_count,
                "segment_timings": segment_timings
            }
            
        except Exception as e:
            print(f"❌ 生成音频失败: {e}")
            raise
    
    def _generate_segment_audio(self, segment: str) -> np.ndarray:
        """生成单个文本段的音频 - 必须成功"""
        generator = self.tts_pipeline(segment, voice=self.voice)
        segment_audio = []
        
        for (_, _, audio_chunk) in generator:
            if isinstance(audio_chunk, torch.Tensor):
                audio_chunk = audio_chunk.cpu().numpy()
            segment_audio.append(audio_chunk)
        
        if not segment_audio:
            raise RuntimeError(f"音频生成失败: {segment[:50]}...")
            
        return np.concatenate(segment_audio)
    
    
