#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
目录常量 - 硬编码的目录结构
"""

# 输出目录结构 - 固定不变
OUTPUT_DIRECTORIES = {
    'chapters': 'chapters',
    'sub_chapters': 'sub_chapters', 
    'sentences': 'sentences',
    'audio': 'audio',
    'subtitles': 'subtitles',
    'analysis': 'analysis',
    'compressed_audio': 'compressed_audio',
    'vocabulary': 'vocabulary'
}

# 输出文件名
OUTPUT_FILES = {
    'statistics': 'meta.json',
    'master_vocabulary': 'master_vocabulary.json'
}

# 音频和压缩设置
AUDIO_SETTINGS = {
    'format': 'wav',
    'compressed_format': 'mp3',
    'bitrate': '64k',
    'sample_rate': 24000
}

# API设置
API_SETTINGS = {
    'base_url': 'https://api.siliconflow.cn/v1',
    'default_model': 'deepseek-ai/DeepSeek-V2.5'
}

# 批量处理设置
BATCH_PROCESSING = {
    'translation_batch_size': 10,  # 参考modules中的max_concurrent_workers
    'analysis_batch_size': 10,     # 分析批量大小
    'api_delay': 0.5              # 批次间延迟
}