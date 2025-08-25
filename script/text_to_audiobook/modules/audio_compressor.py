#!/usr/bin/env python3
"""
音频压缩模块 - 用于压缩生成的人声音频文件
支持MP3、AAC、Opus等格式，预期压缩比85-95%
"""

import os
import logging
from typing import Dict, Tuple
from pydub import AudioSegment
from pydub.utils import which

class AudioCompressor:
    """音频压缩器类"""
    
    def __init__(self, config: Dict):
        """
        初始化音频压缩器
        
        Args:
            config: 压缩配置字典，包含格式、质量等参数
        """
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # 验证ffmpeg是否可用
        if not which("ffmpeg"):
            raise RuntimeError("ffmpeg 未安装或不在PATH中，请先安装ffmpeg")
        
        # 默认压缩配置
        self.default_formats = {
            'mp3': {
                'format': 'mp3',
                'bitrate': '64k',  # 人声音频64kbps足够
                'codec': 'mp3',
                'extension': '.mp3'
            },
            'aac': {
                'format': 'adts',
                'bitrate': '48k',  # AAC更高效，48kbps
                'codec': 'aac',
                'extension': '.aac'
            },
            'opus': {
                'format': 'opus',
                'bitrate': '32k',  # Opus最高效，32kbps
                'codec': 'libopus',
                'extension': '.opus'
            }
        }
        
        self.compression_stats = {
            'total_files': 0,
            'total_original_size': 0,
            'total_compressed_size': 0,
            'compression_ratio': 0.0
        }

    def compress_audio(self, input_path: str, output_path: str, format_name: str = 'mp3') -> bool:
        """
        压缩单个音频文件
        
        Args:
            input_path: 输入音频文件路径
            output_path: 输出音频文件路径
            format_name: 压缩格式名称 ('mp3', 'aac', 'opus')
            
        Returns:
            bool: 压缩是否成功
        """
        try:
            if not os.path.exists(input_path):
                self.logger.error(f"输入文件不存在: {input_path}")
                return False
            
            # 获取压缩格式配置
            format_config = self.config.get('formats', {}).get(format_name)
            if not format_config:
                format_config = self.default_formats.get(format_name, self.default_formats['mp3'])
            
            # 加载音频文件
            audio = AudioSegment.from_file(input_path)
            
            # 创建输出目录
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # 压缩参数
            export_params = {
                'format': format_config['format'],
                'bitrate': format_config['bitrate']
            }
            
            # 针对不同格式添加特定参数
            if format_name == 'mp3':
                export_params.update({
                    'parameters': ['-codec:a', 'mp3', '-q:a', '9']  # 最低质量但足够人声
                })
            elif format_name == 'aac':
                export_params.update({
                    'codec': 'aac',
                    'parameters': ['-profile:a', 'aac_he_v2']  # HE-AAC v2 更高效
                })
            elif format_name == 'opus':
                export_params.update({
                    'codec': 'libopus',
                    'parameters': ['-application', 'voip', '-vbr', 'on']  # VoIP优化
                })
            
            # 导出压缩音频
            audio.export(output_path, **export_params)
            
            # 统计压缩效果
            original_size = os.path.getsize(input_path)
            compressed_size = os.path.getsize(output_path)
            compression_ratio = (1 - compressed_size / original_size) * 100
            
            self.logger.info(f"压缩完成: {input_path} -> {output_path}")
            self.logger.info(f"压缩比: {compression_ratio:.1f}% ({original_size} -> {compressed_size} bytes)")
            
            # 更新统计信息
            self.compression_stats['total_files'] += 1
            self.compression_stats['total_original_size'] += original_size
            self.compression_stats['total_compressed_size'] += compressed_size
            
            return True
            
        except Exception as e:
            self.logger.error(f"压缩失败 {input_path}: {str(e)}")
            return False

    def compress_book_audio(self, book_dir: str, output_subdir: str = "compressed") -> Dict:
        """
        压缩整本书的音频文件
        
        Args:
            book_dir: 书籍目录路径
            output_subdir: 输出子目录名
            
        Returns:
            Dict: 压缩结果统计
        """
        audio_dir = os.path.join(book_dir, 'audio')
        if not os.path.exists(audio_dir):
            self.logger.error(f"音频目录不存在: {audio_dir}")
            return {}
        
        # 获取配置
        enabled_formats = self.config.get('enabled_formats', ['mp3'])
        
        results = {}
        
        for format_name in enabled_formats:
            self.logger.info(f"开始压缩为 {format_name.upper()} 格式...")
            
            # 创建格式特定的输出目录
            format_output_dir = os.path.join(book_dir, output_subdir, format_name)
            os.makedirs(format_output_dir, exist_ok=True)
            
            format_stats = {
                'format': format_name,
                'files_processed': 0,
                'files_success': 0,
                'files_failed': 0,
                'total_original_size': 0,
                'total_compressed_size': 0,
                'compression_ratio': 0.0
            }
            
            # 获取格式扩展名
            extension = self.default_formats[format_name]['extension']
            
            # 遍历音频文件
            for audio_file in os.listdir(audio_dir):
                if not audio_file.lower().endswith(('.wav', '.mp3', '.m4a', '.flac')):
                    continue
                
                input_path = os.path.join(audio_dir, audio_file)
                
                # 生成输出文件名（保持原文件名，改变扩展名）
                base_name = os.path.splitext(audio_file)[0]
                output_file = base_name + extension
                output_path = os.path.join(format_output_dir, output_file)
                
                format_stats['files_processed'] += 1
                
                # 记录原始大小
                original_size = os.path.getsize(input_path)
                format_stats['total_original_size'] += original_size
                
                # 压缩音频
                if self.compress_audio(input_path, output_path, format_name):
                    format_stats['files_success'] += 1
                    
                    # 记录压缩后大小
                    compressed_size = os.path.getsize(output_path)
                    format_stats['total_compressed_size'] += compressed_size
                else:
                    format_stats['files_failed'] += 1
            
            # 计算压缩比
            if format_stats['total_original_size'] > 0:
                format_stats['compression_ratio'] = (
                    1 - format_stats['total_compressed_size'] / format_stats['total_original_size']
                ) * 100
            
            results[format_name] = format_stats
            
            self.logger.info(f"{format_name.upper()} 格式压缩完成:")
            self.logger.info(f"  处理文件: {format_stats['files_processed']}")
            self.logger.info(f"  成功: {format_stats['files_success']}")
            self.logger.info(f"  失败: {format_stats['files_failed']}")
            self.logger.info(f"  压缩比: {format_stats['compression_ratio']:.1f}%")
        
        return results

    def get_compression_stats(self) -> Dict:
        """
        获取总体压缩统计信息
        
        Returns:
            Dict: 压缩统计信息
        """
        if self.compression_stats['total_original_size'] > 0:
            self.compression_stats['compression_ratio'] = (
                1 - self.compression_stats['total_compressed_size'] / 
                self.compression_stats['total_original_size']
            ) * 100
        
        return self.compression_stats.copy()

    def estimate_compression_ratio(self, format_name: str) -> Tuple[float, float]:
        """
        估算指定格式的压缩比范围
        
        Args:
            format_name: 压缩格式名称
            
        Returns:
            Tuple[float, float]: (最小压缩比, 最大压缩比)
        """
        # 基于人声音频的经验数据
        ratios = {
            'mp3': (85.0, 92.0),    # MP3 64kbps
            'aac': (88.0, 94.0),    # AAC HE-v2 48kbps  
            'opus': (90.0, 95.0),   # Opus 32kbps
        }
        
        return ratios.get(format_name, (85.0, 90.0))

    def clean_temp_files(self, temp_dir: str):
        """
        清理临时文件
        
        Args:
            temp_dir: 临时目录路径
        """
        try:
            if os.path.exists(temp_dir):
                for file in os.listdir(temp_dir):
                    file_path = os.path.join(temp_dir, file)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                os.rmdir(temp_dir)
                self.logger.info(f"清理临时文件完成: {temp_dir}")
        except Exception as e:
            self.logger.warning(f"清理临时文件失败: {str(e)}")