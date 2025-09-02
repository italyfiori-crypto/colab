#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
路径工具模块 - 处理文件路径推理
"""

import os
import glob
from typing import List

def get_expected_audio_file(sentence_file: str, output_dir: str) -> str:
    """
    根据句子文件路径推理对应的音频文件路径
    
    Args:
        sentence_file: 句子文件路径 (如 sentences/01_Down_the_Rabbit-Hole(1).txt)
        output_dir: 输出目录
        
    Returns:
        预期的音频文件路径
    """
    filename = os.path.basename(sentence_file)
    audio_filename = os.path.splitext(filename)[0] + '.wav'
    return os.path.join(output_dir, 'audio', audio_filename)


def get_expected_subtitle_file(sentence_file: str, output_dir: str) -> str:
    """
    根据句子文件路径推理对应的字幕文件路径
    
    Args:
        sentence_file: 句子文件路径 (如 sentences/01_Down_the_Rabbit-Hole(1).txt)
        output_dir: 输出目录
        
    Returns:
        预期的字幕文件路径
    """
    filename = os.path.basename(sentence_file)
    subtitle_filename = os.path.splitext(filename)[0] + '.srt'
    return os.path.join(output_dir, 'subtitles', subtitle_filename)

def get_audio_files(book_dir: str) -> List[str]:
    """
    获取书籍目录下的所有音频文件
    """
    return glob.glob(os.path.join(book_dir, 'audio', '*.wav'))

def get_subtitle_files(book_dir: str) -> List[str]:
    """
    获取书籍目录下的所有字幕文件
    """
    return glob.glob(os.path.join(book_dir, 'subtitles', '*.srt'))

def get_sentence_files(book_dir: str) -> List[str]:
    """
    获取书籍目录下的所有句子文件
    """
    return glob.glob(os.path.join(book_dir, 'sentences', '*.txt'))

def get_chapter_files(book_dir: str) -> List[str]:
    return glob.glob(os.path.join(book_dir, 'chapters', '*.txt'))

def get_compressed_audio_files(book_dir: str) -> List[str]:
    """
    获取书籍目录下的所有压缩音频文件
    """
    return glob.glob(os.path.join(book_dir, 'compressed_audio', '*.mp3'))

def get_sub_chapter_files(book_dir: str) -> List[str]:
    """
    获取书籍目录下的所有子章节文件
    """
    return glob.glob(os.path.join(book_dir, 'sub_chapters', '*.txt'))

def get_vocabulary_files(book_dir: str) -> List[str]:
    """
    获取书籍目录下的所有词汇文件
    """
    return glob.glob(os.path.join(book_dir, 'vocabulary', '*.json'))