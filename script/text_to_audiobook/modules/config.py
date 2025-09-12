#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块
包含所有子模块的配置类和统一的配置加载方法
"""

import json
from typing import List
from dataclasses import dataclass
from .sub_chapter_splitter import SubChapterConfig
from .sentence_splitter import SentenceSplitterConfig
from .subtitle_parser import SubtitleParserConfig
from .statistics_collector import StatisticsCollectorConfig


@dataclass
class AudioCompressionConfig:
    """音频压缩配置类"""
    
    # 输出子目录
    output_subdir: str = "compressed_audio"
    
    # 格式配置
    format: dict = None
    
    def __post_init__(self):
        """初始化默认值"""
        if self.format is None:
            self.format = {
                "format": "mp3",
                "bitrate": "64k",
                "codec": "mp3",
                "extension": ".mp3"
            }


@dataclass
class ChapterPattern:
    """章节模式配置类"""
    
    # 模式名称
    name: str
    
    # 多行正则表达式
    multiline_regex: str
    
    # 标题行索引（0开始）
    title_line_index: int
    
    # 内容开始行偏移
    content_start_offset: int


@dataclass
class AudiobookConfig:
    """有声书生成配置类 - 包含所有子模块配置"""
    
    # 章节模式列表
    chapter_patterns: List[ChapterPattern]
    
    # 是否忽略大小写
    ignore_case: bool
    
    # 子章节配置
    sub_chapter: SubChapterConfig
    
    # 句子拆分配置
    sentence: SentenceSplitterConfig
    
    # 字幕翻译配置
    subtitle_parser: SubtitleParserConfig
    
    # 统计收集配置
    statistics: StatisticsCollectorConfig
    
    # 音频压缩配置
    audio_compression: AudioCompressionConfig
    
    @classmethod
    def from_json_file(cls, config_path: str) -> 'AudiobookConfig':
        """
        从JSON配置文件加载配置
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置对象
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        # 处理章节模式配置
        if 'chapter_patterns' in config_data:
            patterns_data = config_data.pop('chapter_patterns')
            patterns = [ChapterPattern(**pattern_data) for pattern_data in patterns_data]
            config_data['chapter_patterns'] = patterns
        
        # 处理子章节配置
        if 'sub_chapter' in config_data:
            sub_config_data = config_data.pop('sub_chapter')
            sub_config = SubChapterConfig(**sub_config_data)
            config_data['sub_chapter'] = sub_config
        
        # 处理句子拆分配置
        if 'sentence' in config_data:
            sentence_config_data = config_data.pop('sentence')
            sentence_config = SentenceSplitterConfig(**sentence_config_data)
            config_data['sentence'] = sentence_config
        
        # 处理字幕翻译配置
        if 'subtitle_parser' in config_data:
            parser_config_data = config_data.pop('subtitle_parser')
            parser_config = SubtitleParserConfig(**parser_config_data)
            config_data['subtitle_parser'] = parser_config
        elif 'subtitle_translator' in config_data:  # 向后兼容旧配置
            parser_config_data = config_data.pop('subtitle_translator')
            parser_config = SubtitleParserConfig(**parser_config_data)
            config_data['subtitle_parser'] = parser_config
        else:
            # 如果配置文件中没有翻译配置，使用默认值
            config_data['subtitle_parser'] = SubtitleParserConfig()
        
        # 处理统计收集配置
        if 'statistics' in config_data:
            statistics_config_data = config_data.pop('statistics')
            statistics_config = StatisticsCollectorConfig(**statistics_config_data)
            config_data['statistics'] = statistics_config
        else:
            # 如果配置文件中没有统计配置，使用默认值
            config_data['statistics'] = StatisticsCollectorConfig()
        
        # 处理音频压缩配置
        if 'audio_compression' in config_data:
            compression_config_data = config_data.pop('audio_compression')
            compression_config = AudioCompressionConfig(**compression_config_data)
            config_data['audio_compression'] = compression_config
        else:
            # 如果配置文件中没有压缩配置，使用默认值
            config_data['audio_compression'] = AudioCompressionConfig()
        
        return cls(**config_data)