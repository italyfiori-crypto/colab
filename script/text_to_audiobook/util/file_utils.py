#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件工具函数
"""

import os
from typing import List


def get_existing_files(output_dir: str, subdir: str, extension: str) -> List[str]:
    """
    获取已存在的文件列表
    
    Args:
        output_dir: 输出根目录
        subdir: 子目录名称
        extension: 文件扩展名（包含点号）
        
    Returns:
        文件路径列表
    """
    target_dir = os.path.join(output_dir, subdir)
    if not os.path.exists(target_dir):
        return []
    
    files = []
    for file in os.listdir(target_dir):
        if file.endswith(extension):
            files.append(os.path.join(target_dir, file))
    
    return sorted(files)


def ensure_directory_exists(directory: str) -> None:
    """
    确保目录存在，不存在则创建
    
    Args:
        directory: 目录路径
    """
    os.makedirs(directory, exist_ok=True)


def get_basename_without_extension(file_path: str) -> str:
    """
    获取文件名（不含扩展名）
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件名（不含扩展名）
    """
    return os.path.splitext(os.path.basename(file_path))[0]