#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置加载器 - 统一配置管理
"""

import json
from typing import List, Optional
from dataclasses import dataclass
from .ai_client import AIConfig


@dataclass
class ChapterPattern:
    """章节模式配置"""
    name: str
    multiline_regex: str
    title_line_index: int
    content_start_offset: int


@dataclass
class TextProcessingConfig:
    """文本处理配置"""
    sub_chapter_max_minutes: int = 5
    words_per_minute: int = 200


@dataclass
class AudioConfig:
    """音频配置"""
    compression_bitrate: str = "64k"
    compression_format: str = "mp3"


@dataclass
class AppConfig:
    """应用配置"""
    chapter_patterns: List[ChapterPattern]
    ignore_case: bool
    text_processing: TextProcessingConfig
    api: AIConfig
    audio: AudioConfig
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AppConfig':
        """从字典创建配置对象"""
        # 处理章节模式
        patterns = []
        if 'chapter_patterns' in data:
            for pattern_data in data['chapter_patterns']:
                patterns.append(ChapterPattern(**pattern_data))
        
        # 处理文本处理配置
        text_config_data = data.get('text_processing', {})
        # 兼容旧配置
        if 'sub_chapter' in data:
            old_config = data['sub_chapter']
            text_config_data.update({
                'sub_chapter_max_minutes': old_config.get('max_reading_minutes', 5),
                'words_per_minute': old_config.get('words_per_minute', 200)
            })
        text_processing = TextProcessingConfig(**text_config_data)
        
        # 处理API配置
        api_config_data = data.get('api', {})
        # 硬编码base_url
        api_config_data['base_url'] = 'https://api.siliconflow.cn/v1'
        
        # 兼容旧配置
        if 'sentence' in data:
            old_config = data['sentence']
            api_config_data.update({
                'api_key': old_config.get('api_key', ''),
                'model': old_config.get('model', 'deepseek-ai/DeepSeek-V2.5'),
                'timeout': old_config.get('timeout', 30)
            })
        elif 'subtitle_parser' in data:
            old_config = data['subtitle_parser']
            api_config_data.update({
                'api_key': old_config.get('api_key', ''),
                'model': old_config.get('model', 'deepseek-ai/DeepSeek-V2.5'),
                'timeout': old_config.get('timeout', 30),
                'max_concurrent_workers': old_config.get('max_concurrent_workers', 20)
            })
        api = AIConfig(**api_config_data)
        
        # 处理音频配置
        audio_config_data = data.get('audio', {})
        # 兼容旧配置
        if 'audio_compression' in data:
            old_config = data['audio_compression']
            if 'format' in old_config:
                format_config = old_config['format']
                audio_config_data.update({
                    'compression_bitrate': format_config.get('bitrate', '64k'),
                    'compression_format': format_config.get('format', 'mp3')
                })
        audio = AudioConfig(**audio_config_data)
        
        return cls(
            chapter_patterns=patterns,
            ignore_case=data.get('ignore_case', True),
            text_processing=text_processing,
            api=api,
            audio=audio
        )


class ConfigLoader:
    """配置加载器"""
    
    @staticmethod
    def load_config(config_path: str) -> AppConfig:
        """
        从JSON文件加载配置
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            应用配置对象
        """
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            return AppConfig.from_dict(config_data)
            
        except Exception as e:
            raise RuntimeError(f"加载配置文件失败 {config_path}: {e}")
    
    @staticmethod
    def validate_config(config: AppConfig) -> None:
        """
        验证配置有效性
        
        Args:
            config: 应用配置
        """
        if not config.api.api_key:
            raise RuntimeError("配置验证失败: 缺少API密钥")
        
        if not config.chapter_patterns:
            raise RuntimeError("配置验证失败: 缺少章节模式配置")
        
        if config.text_processing.sub_chapter_max_minutes <= 0:
            raise RuntimeError("配置验证失败: 子章节最大分钟数必须大于0")
        
