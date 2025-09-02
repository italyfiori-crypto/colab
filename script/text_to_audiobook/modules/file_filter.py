#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件过滤模块 - 处理文件存在性检查和过滤逻辑
"""

import os
import re
from .path_utils import get_expected_audio_file, get_expected_subtitle_file


def check_audio_exists(audio_file: str) -> bool:
    """
    检查音频文件是否存在
    
    Args:
        audio_file: 音频文件路径
        
    Returns:
        文件是否存在
    """
    return os.path.exists(audio_file) and os.path.getsize(audio_file) > 0


def check_subtitle_has_chinese(subtitle_file: str) -> bool:
    """
    检查字幕文件是否已包含中文翻译
    
    Args:
        subtitle_file: 字幕文件路径
        
    Returns:
        是否包含中文翻译
    """
    if not os.path.exists(subtitle_file):
        return False
    
    try:
        with open(subtitle_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # 检查是否包含中文字符
            chinese_pattern = re.compile(r'[\u4e00-\u9fff]+')
            return bool(chinese_pattern.search(content))
    except Exception:
        return False


def filter_files_for_audio_generation(sentence_files: list, output_dir: str) -> tuple:
    """
    过滤需要生成音频的文件
    
    Args:
        sentence_files: 句子文件列表
        output_dir: 输出目录
        
    Returns:
        (需要处理的文件列表, 跳过的文件数量)
    """
    files_to_process = []
    skipped_count = 0
    
    for sentence_file in sentence_files:
        audio_file = get_expected_audio_file(sentence_file, output_dir)
        
        if check_audio_exists(audio_file):
            skipped_count += 1
        else:
            files_to_process.append(sentence_file)
    
    return files_to_process, skipped_count


def filter_files_for_subtitle_translation(subtitle_files: list) -> tuple:
    """
    过滤需要翻译的字幕文件
    
    Args:
        subtitle_files: 字幕文件列表
        
    Returns:
        (需要处理的文件列表, 跳过的文件数量)
    """
    files_to_process = []
    skipped_count = 0
    
    for subtitle_file in subtitle_files:
        if check_subtitle_has_chinese(subtitle_file):
            skipped_count += 1
        else:
            files_to_process.append(subtitle_file)
    
    return files_to_process, skipped_count