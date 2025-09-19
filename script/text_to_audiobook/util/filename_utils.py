#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件名工具 - 统一的文件命名规范
参考modules/chapter_splitter.py中的命名逻辑
"""

import re
import os
from typing import Tuple


def generate_chapter_filename(chapter_num: int, chapter_title: str) -> str:
    """
    生成章节文件名
    
    Args:
        chapter_num: 章节序号
        chapter_title: 章节标题
        
    Returns:
        章节文件名（格式：001_Down_the_Rabbit-Hole.txt）
    """
    # 清理标题中的特殊字符
    clean_title = re.sub(r'[^\w\s-]', '', chapter_title)
    clean_title = re.sub(r'\s+', '_', clean_title.strip())
    
    # 限制标题长度
    if len(clean_title) > 50:
        clean_title = clean_title[:50]
    
    return f"{chapter_num:03d}_{clean_title}.txt"


def generate_sub_filename(base_chapter_filename: str, sub_index: int, extension: str = ".txt") -> str:
    """
    基于章节文件名生成子文件名
    
    Args:
        base_chapter_filename: 基础章节文件名（如001_Down_the_Rabbit-Hole.txt）
        sub_index: 子文件序号
        extension: 文件扩展名
        
    Returns:
        子文件名（格式：001_Down_the_Rabbit-Hole(1).txt）
    """
    base_name = get_basename_without_extension(base_chapter_filename)
    return  f"{base_name}{extension}" if sub_index == 0 else f"{base_name}({sub_index}){extension}"


def get_basename_without_extension(filename: str) -> str:
    """
    获取不带扩展名的文件名
    
    Args:
        filename: 完整文件名
        
    Returns:
        不带扩展名的文件名
    """
    return os.path.splitext(os.path.basename(filename))[0]


def extract_chapter_info_from_filename(filename: str) -> Tuple[int, str]:
    """
    从章节文件名中提取章节信息
    
    Args:
        filename: 章节文件名
        
    Returns:
        (章节序号, 清理后的标题)
    """
    base_name = get_basename_without_extension(filename)
    
    # 匹配格式：001_Down_the_Rabbit-Hole
    match = re.match(r'^(\d{3})_(.+)$', base_name)
    if match:
        chapter_num = int(match.group(1))
        clean_title = match.group(2)
        return chapter_num, clean_title
    
    # 如果不匹配标准格式，尝试从其他格式提取
    if base_name.startswith('chapter_'):
        # 处理chapter_001格式
        match = re.match(r'^chapter_(\d+)$', base_name)
        if match:
            return int(match.group(1)), f"Chapter_{match.group(1)}"
    
    return 1, base_name


def clean_title_for_filename(title: str) -> str:
    """
    清理标题以用于文件名
    
    Args:
        title: 原始标题
        
    Returns:
        清理后的标题
    """
    # 移除标题前的序号（如"Chapter 1: "或"1. "）
    title = re.sub(r'^(Chapter\s*\d+[:：]?\s*|\d+[.．]?\s*)', '', title, flags=re.IGNORECASE)
    
    # 清理特殊字符
    clean_title = re.sub(r'[^\w\s-]', '', title)
    clean_title = re.sub(r'\s+', '_', clean_title.strip())
    
    # 限制长度
    if len(clean_title) > 50:
        clean_title = clean_title[:50]
    
    return clean_title