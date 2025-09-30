#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Edge TTS音频处理器 - 使用微软Edge TTS进行语音合成
"""

import os
import json
import re
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from collections import defaultdict
from infra import FileManager
from infra.config_loader import AppConfig
from util import OUTPUT_DIRECTORIES
import time
import edge_tts
import asyncio


# 支持的Edge TTS语音列表
# 童声: en-US-AnaNeural, en-GB-MaisieNeural
EDGE_TTS_VOICES = [
    'en-GB-LibbyNeural', 'en-GB-MaisieNeural', 'en-GB-RyanNeural', 'en-GB-SoniaNeural', 'en-GB-ThomasNeural', 'en-US-AnaNeural', 'en-US-AndrewMultilingualNeural', 'en-US-AndrewNeural', 'en-US-AriaNeural', 'en-US-AvaMultilingualNeural', 'en-US-AvaNeural', 'en-US-BrianMultilingualNeural', 'en-US-BrianNeural', 'en-US-ChristopherNeural', 'en-US-EmmaMultilingualNeural', 'en-US-EmmaNeural', 'en-US-EricNeural', 'en-US-GuyNeural', 'en-US-JennyNeural', 'en-US-MichelleNeural', 'en-US-RogerNeural', 'en-US-SteffanNeural',
]

@dataclass
class ParagraphAudioData:
    """段落音频数据"""
    paragraph_index: int
    audio_file: str
    srt_file: str
    duration: float
    segments: List[Dict[str, str]]

class EdgeTTSProcessor:
    """Edge TTS音频处理器"""
    
    def __init__(self, config: AppConfig):
        """
        初始化Edge TTS处理器
        
        Args:
            config: 应用配置
        """
        self.config = config
        self.file_manager = FileManager()

    
    def should_use_edge_tts(self, voice: str) -> bool:
        """
        判断是否应该使用Edge TTS
        
        Args:
            voice: 语音模型名称
            
        Returns:
            是否使用Edge TTS
        """
        return voice in EDGE_TTS_VOICES
    
    def generate_audio_files(self, sentence_files: List[str], output_dir: str, voice: str, speed: float) -> Tuple[List[str], List[str]]:
        """
        使用Edge TTS生成音频文件
        
        Args:
            sentence_files: 句子文件列表
            output_dir: 输出目录
            voice: 声音类型
            speed: 语速
            
        Returns:
            (音频文件列表, 字幕文件列表)
        """
        if not sentence_files:
            print(f"⚠️ 未找到句子文件，跳过音频生成")
            return [], []
        
        # 创建输出目录
        audio_dir = os.path.join(output_dir, OUTPUT_DIRECTORIES['audio'])
        subtitle_dir = os.path.join(output_dir, OUTPUT_DIRECTORIES['subtitles'])
        self.file_manager.create_directory(audio_dir)
        self.file_manager.create_directory(subtitle_dir)
        
        print(f"🔊 使用Edge TTS开始音频生成，共 {len(sentence_files)} 个文件...")
        
        audio_files = []
        subtitle_files = []
        
        for i, sentence_file in enumerate(sentence_files, 1):
            try:
                filename = os.path.basename(sentence_file)
                print(f"🔊 Edge TTS生成音频 ({i}/{len(sentence_files)}): {filename}")
                
                # 处理单个文件
                audio_file, subtitle_file = self._process_file(sentence_file, audio_dir, subtitle_dir, voice, speed)
                if audio_file:
                    audio_files.append(audio_file)
                if subtitle_file:
                    subtitle_files.append(subtitle_file)
                
            except Exception as e:
                print(f"❌ Edge TTS音频生成失败 {filename}: {e}")
                continue
        
        print(f"\n✅ Edge TTS音频生成完成! 生成 {len(audio_files)} 个音频文件和 {len(subtitle_files)} 个字幕文件")
        return audio_files, subtitle_files
    
    def _process_file(self, sentence_file: str, audio_dir: str, subtitle_dir: str, voice: str, speed: float) -> Tuple[Optional[str], Optional[str]]:
        """
        处理单个句子文件，生成对应的音频和字幕
        
        Args:
            sentence_file: 句子文件路径（JSONL格式）
            audio_dir: 音频输出目录
            subtitle_dir: 字幕输出目录
            voice: 语音模型
            speed: 语速
            
        Returns:
            (音频文件路径, 字幕文件路径)
        """
        try:
            # 检查文件完整性并提取段落
            is_complete, paragraphs_data = self._extract_paragraphs(sentence_file)
            
            if not is_complete:
                print(f"⚠️ 文件拆分翻译不完整，跳过: {os.path.basename(sentence_file)}")
                return None, None
            
            if not paragraphs_data:
                print(f"⚠️ 文件无有效段落: {os.path.basename(sentence_file)}")
                return None, None
                
        except Exception as e:
            print(f"⚠️ 文件解析失败: {os.path.basename(sentence_file)}, 错误: {e}")
            return None, None
        
        # 生成文件名
        base_name = self.file_manager.get_basename_without_extension(sentence_file)
        final_audio_file = os.path.join(audio_dir, f"{base_name}.wav")
        final_subtitle_file = os.path.join(subtitle_dir, f"{base_name}.jsonl")

        if os.path.exists(final_audio_file) and os.path.exists(final_subtitle_file):
            print(f"🔊 音频文件和字幕文件已经存在, 跳过处理")
            return final_audio_file, final_subtitle_file

        # 生成速度参数
        speed_param = self._format_speed_parameter(speed)
        
        # 为每个段落生成音频和字幕
        paragraph_audio_data = []
        temp_dir = os.path.join(audio_dir, f"temp_{base_name}")
        self.file_manager.create_directory(temp_dir)
        
        try:
            for paragraph_index, segments in paragraphs_data.items():
                paragraph_data = self._generate_paragraph_audio(
                    paragraph_index, segments, temp_dir, voice, speed_param
                )
                if paragraph_data:
                    paragraph_audio_data.append(paragraph_data)
                
                time.sleep(5)
                print(f"  段落 {paragraph_index} 音频生处理完成, 暂停5秒")
            
            if paragraph_audio_data:
                # 合并段落音频和字幕文件
                if self._merge_paragraph_files(paragraph_audio_data, final_audio_file, final_subtitle_file):
                    return final_audio_file, final_subtitle_file
                else:
                    print(f"❌ 文件合并失败: {base_name}")
                    return None, None
            else:
                print(f"❌ 段落音频生成失败: {base_name}")
                return None, None
                
        finally:
            # 清理临时目录
            # self._cleanup_temp_directory(temp_dir)
            pass
    
    def _extract_paragraphs(self, sentence_file: str) -> Tuple[bool, Dict[int, List[Dict[str, str]]]]:
        """
        从句子文件中提取段落数据
        
        Args:
            sentence_file: JSONL句子文件路径
            
        Returns:
            (是否完整, 段落数据字典 {paragraph_index: [segments]})
        """
        try:
            paragraphs_data = defaultdict(list)
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
                        
                        # 提取段落索引和segments
                        paragraph_index = paragraph_data.get('paragraph_index')
                        segments = paragraph_data.get('segments', [])
                        
                        if paragraph_index is not None and segments:
                            for segment in segments:
                                if isinstance(segment, dict) and 'original' in segment and 'translation' in segment:
                                    paragraphs_data[paragraph_index].append({
                                        'original': segment['original'].strip(),
                                        'translation': segment['translation'].strip()
                                    })
                                    
                    except json.JSONDecodeError as e:
                        print(f"      ⚠️ JSON解析失败 行{line_num}: {e}")
                        all_paragraphs_success = False
                        break
            
            return all_paragraphs_success, dict(paragraphs_data)
            
        except Exception as e:
            print(f"      ❌ 文件读取异常: {e}")
            return False, {}
    
    def _generate_paragraph_audio(self, paragraph_index: int, segments: List[Dict[str, str]], 
                                temp_dir: str, voice: str, speed_param: str) -> Optional[ParagraphAudioData]:
        """
        为单个段落生成音频和字幕
        
        Args:
            paragraph_index: 段落索引
            segments: 段落中的句子片段
            temp_dir: 临时目录
            voice: 语音模型
            speed_param: 速度参数
            
        Returns:
            段落音频数据或None
        """
        try:
            # 构建段落文本（句子换行分开）
            paragraph_text = '\n'.join([seg['original'] for seg in segments])
            
            # 生成临时文件名
            temp_audio_file = os.path.join(temp_dir, f"para_{paragraph_index:03d}.mp3")
            temp_srt_file = os.path.join(temp_dir, f"para_{paragraph_index:03d}.srt")

            # 检测文件是否已经存在
            if os.path.exists(temp_audio_file) and os.path.getsize(temp_audio_file) > 0 and \
               os.path.exists(temp_srt_file) and os.path.getsize(temp_srt_file) > 0:
                print(f"⏭️ 段落 {paragraph_index} 音频和字幕文件已存在且有内容，跳过生成。")
                duration = self._get_audio_duration_from_srt(temp_srt_file)
                return ParagraphAudioData(
                    paragraph_index=paragraph_index,
                    audio_file=temp_audio_file,
                    srt_file=temp_srt_file,
                    duration=duration,
                    segments=segments
                )
            
            # 使用Edge TTS生成音频和字幕
            if self._generate_audio_with_edge_tts(paragraph_text, temp_audio_file, temp_srt_file, voice, speed_param):
                # 获取音频时长
                duration = self._get_audio_duration_from_srt(temp_srt_file)
                
                return ParagraphAudioData(
                    paragraph_index=paragraph_index,
                    audio_file=temp_audio_file,
                    srt_file=temp_srt_file,
                    duration=duration,
                    segments=segments
                )
            else:
                print(f"❌ 段落 {paragraph_index} 音频生成失败")
                return None
                
        except Exception as e:
            print(f"❌ 处理段落 {paragraph_index} 失败: {e}")
            return None
    
    def _generate_audio_with_edge_tts(self, text: str, audio_file: str, srt_file: str, voice: str, speed_param: str) -> bool:
        """
        使用Edge TTS生成音频和字幕
        
        Args:
            text: 要转换的文本
            audio_file: 输出音频文件路径
            srt_file: 输出字幕文件路径
            voice: 语音模型
            speed_param: 速度参数
            
        Returns:
            是否生成成功
        """
        try:
            # 运行异步生成
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(
                    self._async_generate_audio(text, audio_file, srt_file, voice, speed_param)
                )
            finally:
                loop.close()
                
        except Exception as e:
            print(f"❌ Edge TTS生成异常: {e}")
            return False
    
    async def _async_generate_audio(self, text: str, audio_file: str, srt_file: str, voice: str, speed_param: str) -> bool:
        """
        异步生成音频和字幕
        """
        try:
            # 创建Edge TTS通信对象
            communicate = edge_tts.Communicate(text, voice, rate=speed_param)
            submaker = edge_tts.SubMaker()
            
            # 生成音频和字幕数据
            with open(audio_file, "wb") as audio_f:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_f.write(chunk["data"])
                    elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                        submaker.feed(chunk)
            
            # 生成字幕文件
            with open(srt_file, "w", encoding="utf-8") as srt_f:
                srt_f.write(submaker.get_srt())
            
            return True
            
        except Exception as e:
            print(f"❌ 异步音频生成失败: {e}")
            return False
    
    def _format_speed_parameter(self, speed: float) -> str:
        """
        格式化速度参数为Edge TTS支持的格式
        
        Args:
            speed: 速度倍数（如0.8, 1.0, 1.2等）
            
        Returns:
            Edge TTS速度参数字符串
        """
        if speed == 1.0:
            return "+0%"
        elif speed > 1.0:
            # 加速：速度大于1.0时转换为正百分比
            percentage = int((speed - 1.0) * 100)
            return f"+{percentage}%"
        else:
            # 减速：速度小于1.0时转换为负百分比
            percentage = int((1.0 - speed) * 100)
            return f"-{percentage}%"
    
    def _get_audio_duration_from_srt(self, srt_file: str) -> float:
        """
        从SRT文件中获取音频总时长
        
        Args:
            srt_file: SRT字幕文件路径
            
        Returns:
            音频时长（秒）
        """
        try:
            with open(srt_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 查找最后一个时间戳
            time_pattern = r'(\d{2}):(\d{2}):(\d{2}),(\d{3}) --> (\d{2}):(\d{2}):(\d{2}),(\d{3})'
            matches = re.findall(time_pattern, content)
            
            if matches:
                # 获取最后一个结束时间
                last_match = matches[-1]
                end_hours, end_minutes, end_seconds, end_ms = map(int, last_match[4:8])
                total_seconds = end_hours * 3600 + end_minutes * 60 + end_seconds + end_ms / 1000.0
                return total_seconds
            else:
                return 0.0
                
        except Exception as e:
            print(f"❌ 获取音频时长失败: {e}")
            return 0.0
    
    def _merge_paragraph_files(self, paragraph_data_list: List[ParagraphAudioData], 
                             final_audio_file: str, final_subtitle_file: str) -> bool:
        """
        合并段落音频文件和字幕文件
        
        Args:
            paragraph_data_list: 段落音频数据列表
            final_audio_file: 最终音频文件路径
            final_subtitle_file: 最终字幕文件路径
            
        Returns:
            合并是否成功
        """
        try:
            # 按段落索引排序
            paragraph_data_list.sort(key=lambda x: x.paragraph_index)
            
            # 合并音频文件
            if not self._merge_audio_files(paragraph_data_list, final_audio_file):
                return False
            
            # 合并字幕文件
            if not self._merge_subtitle_files(paragraph_data_list, final_subtitle_file):
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ 文件合并失败: {e}")
            return False
    
    def _merge_audio_files(self, paragraph_data_list: List[ParagraphAudioData], output_file: str) -> bool:
        """
        合并音频文件
        """
        try:
            # 尝试使用pydub合并音频
            from pydub import AudioSegment
            
            merged_audio = AudioSegment.empty()
            
            for paragraph_data in paragraph_data_list:
                if os.path.exists(paragraph_data.audio_file):
                    segment = AudioSegment.from_mp3(paragraph_data.audio_file)
                    merged_audio += segment
            
            # 导出为WAV格式以保持与现有系统兼容
            merged_audio.export(output_file, format="wav")
            return True
            
        except ImportError:
            print("⚠️ pydub库不可用，尝试使用系统命令合并音频")
            return self._merge_audio_with_system_command(paragraph_data_list, output_file)
        except Exception as e:
            print(f"❌ 音频合并失败: {e}")
            return False
    
    def _merge_audio_with_system_command(self, paragraph_data_list: List[ParagraphAudioData], output_file: str) -> bool:
        """
        使用系统命令合并音频（ffmpeg）
        """
        try:
            import subprocess
            
            # 创建临时文件列表
            file_list_path = output_file + ".filelist"
            with open(file_list_path, 'w') as f:
                for paragraph_data in paragraph_data_list:
                    if os.path.exists(paragraph_data.audio_file):
                        f.write(f"file '{paragraph_data.audio_file}'\n")
            
            # 使用ffmpeg合并
            cmd = [
                'ffmpeg', '-y', '-f', 'concat', '-safe', '0',
                '-i', file_list_path, '-c', 'copy', output_file
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # 清理临时文件
            if os.path.exists(file_list_path):
                os.remove(file_list_path)
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"❌ 系统命令音频合并失败: {e}")
            return False
    
    def _merge_subtitle_files(self, paragraph_data_list: List[ParagraphAudioData], output_file: str) -> bool:
        """
        合并字幕文件并转换为JSONL格式
        """
        try:
            merged_subtitles = []
            cumulative_time = 0.0
            entry_index = 1
            
            for paragraph_data in paragraph_data_list:
                if os.path.exists(paragraph_data.srt_file):
                    # 读取SRT内容并转换为JSONL条目
                    jsonl_entries = self._convert_srt_to_jsonl(
                        paragraph_data.srt_file, 
                        cumulative_time, 
                        entry_index,
                        paragraph_data.segments
                    )
                    
                    merged_subtitles.extend(jsonl_entries)
                    entry_index += len(jsonl_entries)
                    cumulative_time += paragraph_data.duration
            
            # 写入JSONL文件
            with open(output_file, 'w', encoding='utf-8') as f:
                for entry in merged_subtitles:
                    f.write(json.dumps(entry, ensure_ascii=False, separators=(',', ':')) + '\n')
            
            return True
            
        except Exception as e:
            print(f"❌ 字幕合并失败: {e}")
            return False
    
    def _convert_srt_to_jsonl(self, srt_file: str, base_timestamp: float, start_index: int, segments: List[Dict[str, str]]) -> List[Dict]:
        """
        将SRT文件转换为JSONL格式条目
        
        Args:
            srt_file: SRT文件路径
            base_timestamp: 基础时间偏移
            start_index: 起始索引
            segments: 段落的句子片段（用于获取中文翻译）
            
        Returns:
            JSONL条目列表
        """
        try:
            with open(srt_file, 'r', encoding='utf-8') as f:
                srt_content = f.read()
            
            # 解析SRT条目
            srt_pattern = r'(\d+)\n(\d{2}):(\d{2}):(\d{2}),(\d{3}) --> (\d{2}):(\d{2}):(\d{2}),(\d{3})\n(.+?)(?=\n\n|\n$)'
            matches = re.findall(srt_pattern, srt_content, re.DOTALL)
            
            jsonl_entries = []
            
            for i, match in enumerate(matches):
                # 解析时间戳
                start_h, start_m, start_s, start_ms = map(int, match[1:5])
                end_h, end_m, end_s, end_ms = map(int, match[5:9])
                
                start_seconds = start_h * 3600 + start_m * 60 + start_s + start_ms / 1000.0
                end_seconds = end_h * 3600 + end_m * 60 + end_s + end_ms / 1000.0
                
                # 添加基础时间偏移
                adjusted_start = start_seconds + base_timestamp
                adjusted_end = end_seconds + base_timestamp
                
                # 格式化时间戳
                start_timestamp = self._format_timestamp(adjusted_start)
                end_timestamp = self._format_timestamp(adjusted_end)
                timestamp = f"{start_timestamp} --> {end_timestamp}"
                
                # 获取英文文本
                english_text = match[9].strip()
                
                # 查找对应的中文翻译
                chinese_text = ""
                if i < len(segments):
                    chinese_text = segments[i].get('translation', '')
                
                # 构建JSONL条目
                entry = {
                    "index": start_index + i,
                    "timestamp": timestamp,
                    "english_text": english_text,
                    "chinese_text": chinese_text
                }
                
                jsonl_entries.append(entry)
            
            return jsonl_entries
            
        except Exception as e:
            print(f"❌ SRT转JSONL失败: {e}")
            return []
    
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
    
    def _cleanup_temp_directory(self, temp_dir: str):
        """
        清理临时目录
        
        Args:
            temp_dir: 临时目录路径
        """
        try:
            import shutil
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"⚠️ 清理临时目录失败: {e}")