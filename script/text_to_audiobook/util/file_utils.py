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


def find_txt_files(input_path: str) -> List[str]:
    """
    查找 .txt 文件
    
    Args:
        input_path: 输入路径（文件或目录）
        
    Returns:
        .txt 文件路径列表
        
    Raises:
        ValueError: 如果路径不存在或无效
    """
    if not os.path.exists(input_path):
        raise ValueError(f"路径不存在: {input_path}")
    
    # 如果是文件
    if os.path.isfile(input_path):
        if input_path.lower().endswith('.txt'):
            return [input_path]
        else:
            raise ValueError(f"输入文件必须是 .txt 格式: {input_path}")
    
    # 如果是目录
    elif os.path.isdir(input_path):
        txt_files = []
        for file in os.listdir(input_path):
            if file.lower().endswith('.txt'):
                txt_files.append(os.path.join(input_path, file))
        
        if not txt_files:
            raise ValueError(f"目录中未找到 .txt 文件: {input_path}")
        
        return sorted(txt_files)
    
    else:
        raise ValueError(f"无效路径类型: {input_path}")