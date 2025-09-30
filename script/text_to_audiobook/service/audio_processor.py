#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频处理服务 - 统一的音频生成和压缩功能
"""

import os
import json
import numpy as np
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from infra import FileManager
from infra.config_loader import AppConfig
from util import OUTPUT_DIRECTORIES
from .edge_tts_processor import EdgeTTSProcessor

# 音频处理依赖
try:
    import torch
    import soundfile as sf
    from kokoro import KPipeline
    AUDIO_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 音频依赖不可用: {e}")
    AUDIO_AVAILABLE = False


@dataclass
class AudioProcessingConfig:
    """音频处理配置"""
    voice: str = ""
    speed: float = 0
    sample_rate: int = 24000
    audio_format: str = "wav"
    subtitle_format: str = "jsonl"


class AudioProcessor:
    """统一的音频处理器"""
    
    def __init__(self, config: AppConfig):
        """
        初始化音频处理器
        
        Args:
            config: 应用配置
        """
        self.config = config
        self.file_manager = FileManager()
        self.audio_config = AudioProcessingConfig()
        
        # 初始化Edge TTS处理器
        self.edge_tts_processor = EdgeTTSProcessor(config)
        
        # 初始化Kokoro TTS
        if AUDIO_AVAILABLE:
            try:
                self.tts_pipeline = KPipeline(lang_code='a')  # 'a' for American English
                print("✅ Kokoro TTS管道加载成功")
            except Exception as e:
                print(f"❌ Kokoro TTS管道初始化失败: {e}")
                self.tts_pipeline = None
        else:
            self.tts_pipeline = None
            print("⚠️ 音频依赖不可用，音频功能将被跳过")
    
    def generate_audio_files(self, sentence_files: List[str], output_dir: str, voice: str, speed: float) -> Tuple[List[str], List[str]]:
        """
        生成音频文件
        
        Args:
            sentence_files: 句子文件列表
            output_dir: 输出目录
            voice: 声音类型
            speed: 语速
            
        Returns:
            (音频文件列表, 字幕文件列表)
        """
        # 检查是否使用Edge TTS
        if self.edge_tts_processor.should_use_edge_tts(voice):
            print(f"🔊 使用Edge TTS进行音频生成，语音: {voice}")
            return self.edge_tts_processor.generate_audio_files(sentence_files, output_dir, voice, speed)
        
        # 使用原有的Kokoro TTS逻辑
        if not self.tts_pipeline:
            print(f"🔊 TTS管道不可用，跳过音频生成")
            return [], []
        
        if not sentence_files:
            print(f"⚠️ 未找到句子文件，跳过音频生成")
            return [], []
        
        # 更新配置
        self.audio_config.voice = voice
        self.audio_config.speed = speed
        
        # 创建输出目录
        audio_dir = os.path.join(output_dir, OUTPUT_DIRECTORIES['audio'])
        subtitle_dir = os.path.join(output_dir, OUTPUT_DIRECTORIES['subtitles'])
        self.file_manager.create_directory(audio_dir)
        self.file_manager.create_directory(subtitle_dir)
        
        print(f"🔊 开始音频生成，共 {len(sentence_files)} 个文件...")
        
        audio_files = []
        subtitle_files = []
        
        for i, sentence_file in enumerate(sentence_files, 1):
            try:
                filename = os.path.basename(sentence_file)
                print(f"🔊 生成音频 ({i}/{len(sentence_files)}): {filename}")
                
                # 处理单个文件
                audio_file, subtitle_file = self._process_file(sentence_file, audio_dir, subtitle_dir)
                if audio_file:
                    audio_files.append(audio_file)
                if subtitle_file:
                    subtitle_files.append(subtitle_file)
                
            except Exception as e:
                print(f"❌ 音频生成失败 {filename}: {e}")
                continue
        
        print(f"\n✅ 音频生成完成! 生成 {len(audio_files)} 个音频文件和 {len(subtitle_files)} 个字幕文件")
        return audio_files, subtitle_files
    
    def _process_file(self, sentence_file: str, audio_dir: str, subtitle_dir: str) -> Tuple[Optional[str], Optional[str]]:
        """
        处理单个句子文件（JSONL格式），生成对应的音频和字幕
        
        Args:
            sentence_file: 句子文件路径（JSONL格式）
            audio_dir: 音频输出目录
            subtitle_dir: 字幕输出目录
            
        Returns:
            (音频文件路径, 字幕文件路径)
        """
        try:
            # 检查文件完整性并提取句子
            is_complete, segments_data = self._check_file_completeness(sentence_file)
            
            if not is_complete:
                print(f"⚠️ 文件拆分翻译不完整，跳过: {os.path.basename(sentence_file)}")
                return None, None
            
            if not segments_data:
                print(f"⚠️ 文件无有效句子片段: {os.path.basename(sentence_file)}")
                return None, None
                
        except Exception as e:
            print(f"⚠️ 文件解析失败: {os.path.basename(sentence_file)}, 错误: {e}")
            return None, None
        
        # 提取英文句子用于音频生成
        english_sentences = [seg['original'] for seg in segments_data]
        
        # 生成文件名
        base_name = self.file_manager.get_basename_without_extension(sentence_file)
        audio_file = os.path.join(audio_dir, f"{base_name}.{self.audio_config.audio_format}")
        subtitle_file = os.path.join(subtitle_dir, f"{base_name}.{self.audio_config.subtitle_format}")

        if os.path.exists(audio_file) and os.path.exists(subtitle_file):
            print(f"🔊 音频文件和字幕文件已经存在, 跳过处理")
            return audio_file, subtitle_file

        # 为每个句子单独生成音频并获取真实时长
        temp_audio_files, durations = self._generate_individual_audios(english_sentences, base_name, audio_dir)
        
        if temp_audio_files and durations:
            # 将单句音频合并为完整音频文件
            if self._merge_audio_files(temp_audio_files, audio_file):
                # 使用真实时长生成双语字幕文件
                self._generate_bilingual_subtitle_file(segments_data, durations, subtitle_file)
                return audio_file, subtitle_file
            else:
                print(f"❌ 音频合并失败: {base_name}")
                return None, None
        else:
            print(f"❌ 单句音频生成失败: {base_name}")
            return None, None
    
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
            temp_audio_file = os.path.join(audio_dir, f"{base_name}_temp_{i:03d}.{self.audio_config.audio_format}")
            
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
            generator = self.tts_pipeline(text, voice=self.audio_config.voice, speed=self.audio_config.speed)
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
            sf.write(output_path, audio, self.audio_config.sample_rate)
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
                if sample_rate != self.audio_config.sample_rate:
                    print(f"⚠️ 采样率不匹配: {audio_file} ({sample_rate} vs {self.audio_config.sample_rate})")
                audio_chunks.append(audio_data)
            
            # 合并音频数据
            if audio_chunks:
                merged_audio = np.concatenate(audio_chunks)
                sf.write(output_path, merged_audio, self.audio_config.sample_rate)
                
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
        self.file_manager.write_text_file(output_path, '\n'.join(srt_content))
    
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
    
    def compress_audio_files(self, audio_files: List[str], output_dir: str) -> bool:
        """
        压缩音频文件（WAV转MP3）
        
        Args:
            audio_files: 音频文件列表
            output_dir: 输出目录
            
        Returns:
            是否压缩成功
        """
        if not audio_files:
            print(f"⚠️ 未找到音频文件，跳过压缩")
            return True
        
        try:
            # 尝试导入pydub进行音频压缩
            from pydub import AudioSegment
            
            # 创建压缩音频目录
            compressed_dir = os.path.join(output_dir, OUTPUT_DIRECTORIES['compressed_audio'])
            self.file_manager.create_directory(compressed_dir)
            
            print(f"🗜️ 开始音频压缩，共 {len(audio_files)} 个文件...")
            
            success_count = 0
            for i, audio_file in enumerate(audio_files, 1):
                try:
                    filename = os.path.basename(audio_file)
                    base_name = self.file_manager.get_basename_without_extension(filename)
                    output_file = os.path.join(compressed_dir, f"{base_name}.mp3")
                    
                    # 加载WAV文件并转换为MP3
                    audio = AudioSegment.from_wav(audio_file)
                    audio.export(output_file, format="mp3", bitrate="64k")
                    
                    success_count += 1
                    print(f"🗜️ 压缩完成 ({i}/{len(audio_files)}): {filename}")
                    
                except Exception as e:
                    print(f"❌ 压缩失败 {filename}: {e}")
                    continue
            
            print(f"\n✅ 音频压缩完成! 成功压缩 {success_count}/{len(audio_files)} 个文件")
            return success_count > 0
            
        except ImportError:
            print(f"⚠️ pydub库不可用，跳过音频压缩")
            return True
        except Exception as e:
            print(f"❌ 音频压缩失败: {e}")
            return False
    
    def _check_file_completeness(self, sentence_file: str) -> Tuple[bool, List[Dict[str, str]]]:
        """
        检查JSONL文件的完整性并提取句子片段
        
        Args:
            sentence_file: JSONL句子文件路径
            
        Returns:
            (是否完整, 句子片段列表)
        """
        try:
            segments_data = []
            all_paragraphs_success = True
            
            with open(sentence_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        paragraph_data = json.loads(line)
                        
                        # 检查必需字段
                        if not isinstance(paragraph_data, dict):
                            continue
                        
                        # 检查success状态
                        if not paragraph_data.get('success', False):
                            all_paragraphs_success = False
                            break
                        
                        # 提取segments
                        segments = paragraph_data.get('segments', [])
                        if segments:
                            for segment in segments:
                                if isinstance(segment, dict) and 'original' in segment and 'translation' in segment:
                                    segments_data.append({
                                        'original': segment['original'].strip(),
                                        'translation': segment['translation'].strip()
                                    })
                                    
                    except json.JSONDecodeError as e:
                        print(f"      ⚠️ JSON解析失败 行{line_num}: {e}")
                        all_paragraphs_success = False
                        break
            
            return all_paragraphs_success, segments_data
            
        except Exception as e:
            print(f"      ❌ 文件读取异常: {e}")
            return False, []
    
    def _generate_bilingual_subtitle_file(self, segments_data: List[Dict[str, str]], durations: List[float], subtitle_file: str):
        """
        生成双语字幕文件（JSONL格式）
        
        Args:
            segments_data: 句子片段数据 [{"original": "英文", "translation": "中文"}, ...]
            durations: 每个句子的音频时长列表
            subtitle_file: 字幕文件路径
        """
        try:
            import json
            
            with open(subtitle_file, 'w', encoding='utf-8') as f:
                current_time = 0.0
                
                for i, (segment, duration) in enumerate(zip(segments_data, durations), 1):
                    # 计算时间戳
                    start_time = current_time
                    end_time = current_time + duration
                    current_time = end_time
                    
                    # 格式化时间戳
                    start_timestamp = self._format_timestamp(start_time)
                    end_timestamp = self._format_timestamp(end_time)
                    timestamp = f"{start_timestamp} --> {end_timestamp}"
                    
                    # 构建JSONL条目
                    entry = {
                        "index": i,
                        "timestamp": timestamp,
                        "english_text": segment['original'],
                        "chinese_text": segment['translation']
                    }
                    
                    # 写入JSONL条目
                    f.write(json.dumps(entry, ensure_ascii=False, separators=(',', ':')) + '\n')
                    
        except Exception as e:
            print(f"❌ 生成双语字幕文件失败: {e}")
    
    def _format_timestamp(self, seconds: float) -> str:
        """
        格式化时间戳为SRT格式
        
        Args:
            seconds: 秒数
            
        Returns:
            SRT格式时间戳
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millisecs = int((seconds - int(seconds)) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"
    
    