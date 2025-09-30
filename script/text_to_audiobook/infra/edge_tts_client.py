#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Edge TTS 客户端 - 专门处理Edge TTS语音合成
"""

import asyncio
import edge_tts
from typing import Optional


# 支持的Edge TTS语音列表
EDGE_TTS_VOICES = [
    'en-GB-LibbyNeural', 'en-GB-MaisieNeural', 'en-GB-RyanNeural', 'en-GB-SoniaNeural', 'en-GB-ThomasNeural', 
    'en-US-AnaNeural', 'en-US-AndrewMultilingualNeural', 'en-US-AndrewNeural', 'en-US-AriaNeural', 
    'en-US-AvaMultilingualNeural', 'en-US-AvaNeural', 'en-US-BrianMultilingualNeural', 'en-US-BrianNeural', 
    'en-US-ChristopherNeural', 'en-US-EmmaMultilingualNeural', 'en-US-EmmaNeural', 'en-US-EricNeural', 
    'en-US-GuyNeural', 'en-US-JennyNeural', 'en-US-MichelleNeural', 'en-US-RogerNeural', 'en-US-SteffanNeural'
]


class EdgeTTSClient:
    """Edge TTS客户端，专门处理Edge TTS语音合成"""
    
    def __init__(self):
        """初始化Edge TTS客户端"""
        pass
    
    def should_use_edge_tts(self, voice: str) -> bool:
        """
        判断是否应该使用Edge TTS
        
        Args:
            voice: 语音模型名称
            
        Returns:
            是否使用Edge TTS
        """
        return voice in EDGE_TTS_VOICES
    
    def generate_sentence_audio(self, text: str, output_file: str, voice: str, speed: float) -> float:
        """
        为单个句子生成音频，返回时长
        
        Args:
            text: 句子文本
            output_file: 输出音频文件（会自动转换为MP3格式）
            voice: 语音模型
            speed: 语速
            
        Returns:
            音频时长（秒），失败时返回0
        """
        try:
            # Edge TTS生成MP3格式，需要转换文件扩展名
            import os
            mp3_file = os.path.splitext(output_file)[0] + '.mp3'
            
            # 格式化速度参数
            speed_param = self._format_speed_parameter(speed)
            
            # 运行异步生成
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                success = loop.run_until_complete(
                    self._async_generate_single_sentence(text, mp3_file, voice, speed_param)
                )
                if success:
                    # 如果需要WAV格式，转换格式
                    if output_file.lower().endswith('.wav'):
                        self._convert_mp3_to_wav(mp3_file, output_file)
                        # 删除临时MP3文件
                        if os.path.exists(mp3_file):
                            os.remove(mp3_file)
                        return self._get_audio_duration_from_file(output_file)
                    else:
                        return self._get_audio_duration_from_file(mp3_file)
                else:
                    return 0.0
            finally:
                loop.close()
                
        except Exception as e:
            print(f"❌ Edge TTS单句音频生成异常: {e}")
            return 0.0
    
    async def _async_generate_single_sentence(self, text: str, audio_file: str, voice: str, speed_param: str) -> bool:
        """
        异步生成单句音频
        """
        try:
            # 创建Edge TTS通信对象
            communicate = edge_tts.Communicate(text, voice, rate=speed_param)
            
            # 生成音频数据
            with open(audio_file, "wb") as audio_f:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_f.write(chunk["data"])
            
            return True
            
        except Exception as e:
            print(f"❌ 异步单句音频生成失败: {e}")
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
    
    def _convert_mp3_to_wav(self, mp3_file: str, wav_file: str) -> bool:
        """
        将MP3文件转换为WAV格式
        
        Args:
            mp3_file: MP3文件路径
            wav_file: WAV文件路径
            
        Returns:
            转换是否成功
        """
        try:
            from pydub import AudioSegment
            audio = AudioSegment.from_mp3(mp3_file)
            audio.export(wav_file, format="wav")
            return True
        except ImportError:
            # 备用方案：使用ffmpeg
            try:
                import subprocess
                cmd = ['ffmpeg', '-y', '-i', mp3_file, wav_file]
                result = subprocess.run(cmd, capture_output=True, text=True)
                return result.returncode == 0
            except:
                return False
        except Exception as e:
            print(f"❌ MP3转WAV失败: {e}")
            return False
    
    def _get_audio_duration_from_file(self, audio_file: str) -> float:
        """
        从音频文件获取时长
        
        Args:
            audio_file: 音频文件路径
            
        Returns:
            音频时长（秒）
        """
        try:
            from pydub import AudioSegment
            # 根据文件扩展名选择正确的加载方法
            if audio_file.lower().endswith('.mp3'):
                audio = AudioSegment.from_mp3(audio_file)
            elif audio_file.lower().endswith('.wav'):
                audio = AudioSegment.from_wav(audio_file)
            else:
                audio = AudioSegment.from_file(audio_file)
            return len(audio) / 1000.0  # 转换为秒
        except ImportError:
            # 备用方案：使用ffprobe
            try:
                import subprocess
                cmd = ['ffprobe', '-v', 'quiet', '-show_entries', 'format=duration', '-of', 'csv=p=0', audio_file]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode == 0:
                    return float(result.stdout.strip())
            except:
                pass
            return 0.0
        except Exception as e:
            print(f"❌ 获取音频时长失败: {e}")
            return 0.0