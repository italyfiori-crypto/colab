#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频生成模块
使用Kokoro TTS生成语音音频
"""

from pathlib import Path
from typing import Optional, Dict
import numpy as np

try:
    import torch
    import soundfile as sf
    from kokoro import KPipeline
except ImportError:
    torch = None
    sf = None
    KPipeline = None


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
        self.tts_pipeline = None
        self.simulate_mode = False
        
        # 初始化Kokoro管道
        self._init_tts_pipeline()
    
    def _init_tts_pipeline(self):
        """初始化TTS管道"""
        if not KPipeline:
            print("Kokoro库未安装，将使用模拟模式")
            self.simulate_mode = True
            return
        
        try:
            self.tts_pipeline = KPipeline(lang_code='a')  # 'a' for American English
            print("Kokoro TTS管道加载成功")
        except Exception as e:
            print(f"Kokoro TTS管道加载失败: {e}")
            print("将使用模拟模式（仅生成字幕文件）")
            self.simulate_mode = True
    
    def generate_audio(self, text: str, output_path: Path, text_splitter) -> Dict:
        """
        生成音频文件
        
        Args:
            text: 要转换的文本
            output_path: 输出音频文件路径
            text_splitter: 文本分割器实例
            
        Returns:
            包含音频统计信息和分段时间信息的字典: {
                'duration': float,
                'segments_count': int,
                'segment_timings': [{'text': str, 'start_time': float, 'end_time': float, 'duration': float}]
            }
        """
        if self.simulate_mode:
            return self._simulate_audio_generation(text, text_splitter)
        
        try:
            print(f"正在生成音频: {output_path.name}")
            print(f"文本长度: {len(text)} 字符")
            
            # 分段处理长文本（每段最多300字符）
            segments = text_splitter.split_text(text, max_length=300)
            segments_count = len(segments)
            
            # 生成各段的音频并记录时间信息
            all_audio = []
            segment_timings = []
            current_time = 0.0
            
            for i, segment in enumerate(segments):
                if segment.strip():
                    print(f"  处理第 {i+1}/{segments_count} 段...")
                    segment_audio = self._generate_segment_audio(segment)
                    if segment_audio is not None:
                        # 计算当前段的时长
                        segment_duration = len(segment_audio) / self.sample_rate
                        
                        # 记录分段时间信息
                        segment_timings.append({
                            'text': segment.strip(),
                            'start_time': current_time,
                            'end_time': current_time + segment_duration,
                            'duration': segment_duration
                        })
                        
                        all_audio.append(segment_audio)
                        current_time += segment_duration
                        
                        print(f"    段时长: {segment_duration:.3f}秒")
            
            if not all_audio:
                print("没有成功生成任何音频段")
                return {
                    "duration": 0.0, 
                    "segments_count": segments_count,
                    "segment_timings": []
                }
            
            # 合并所有音频段
            audio = np.concatenate(all_audio)
            
            # 保存音频文件
            sf.write(str(output_path), audio, self.sample_rate)
            
            # 计算音频时长
            duration = len(audio) / self.sample_rate
            
            print(f"音频生成完成，时长: {duration:.2f}秒")
            print(f"共生成 {len(segment_timings)} 个音频段")
            return {
                "duration": duration, 
                "segments_count": segments_count,
                "segment_timings": segment_timings
            }
            
        except Exception as e:
            print(f"生成音频时出错: {e}")
            return {"duration": 0.0, "segments_count": 0}
    
    def _generate_segment_audio(self, segment: str) -> Optional[np.ndarray]:
        """生成单个文本段的音频"""
        try:
            generator = self.tts_pipeline(segment, voice=self.voice)
            segment_audio = []
            
            for j, (graphemes, phonemes, audio_chunk) in enumerate(generator):
                if isinstance(audio_chunk, torch.Tensor):
                    audio_chunk = audio_chunk.cpu().numpy()
                segment_audio.append(audio_chunk)
            
            if segment_audio:
                return np.concatenate(segment_audio)
            else:
                return None
                
        except Exception as e:
            print(f"  段音频生成失败: {e}")
            return None
    
    def _simulate_audio_generation(self, text: str, text_splitter) -> Dict:
        """模拟模式下的音频时长估算"""
        print("使用模拟模式生成音频时长估算")
        word_count = len(text.split())
        estimated_duration = (word_count / self.words_per_minute) * 60
        
        # 计算分段数和模拟时间信息
        segments = text_splitter.split_text(text, max_length=300)
        segments_count = len(segments)
        
        # 为每个段估算时间
        segment_timings = []
        current_time = 0.0
        
        for segment in segments:
            if segment.strip():
                # 基于单词数估算段时长
                segment_words = len(segment.split())
                segment_duration = (segment_words / self.words_per_minute) * 60
                
                segment_timings.append({
                    'text': segment.strip(),
                    'start_time': current_time,
                    'end_time': current_time + segment_duration,
                    'duration': segment_duration
                })
                
                current_time += segment_duration
        
        print(f"估算音频时长: {estimated_duration:.2f}秒")
        print(f"分段数量: {segments_count}")
        return {
            "duration": estimated_duration, 
            "segments_count": segments_count,
            "segment_timings": segment_timings
        }