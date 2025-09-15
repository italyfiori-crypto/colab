#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件管理器 - 统一文件操作
"""

import os
import glob
import shutil
from typing import List, Optional, Tuple
from pathlib import Path


class FileManager:
    """统一的文件管理器"""
    
    @staticmethod
    def read_text_file(file_path: str, encoding: str = 'utf-8') -> str:
        """
        读取文本文件
        
        Args:
            file_path: 文件路径
            encoding: 编码格式
            
        Returns:
            文件内容
        """
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except Exception as e:
            raise RuntimeError(f"读取文件失败 {file_path}: {e}")
    
    @staticmethod
    def write_text_file(file_path: str, content: str, encoding: str = 'utf-8') -> None:
        """
        写入文本文件
        
        Args:
            file_path: 文件路径
            content: 文件内容
            encoding: 编码格式
        """
        try:
            # 确保目录存在
            FileManager.create_directory(os.path.dirname(file_path))
            
            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)
        except Exception as e:
            raise RuntimeError(f"写入文件失败 {file_path}: {e}")
    
    @staticmethod
    def create_directory(dir_path: str) -> None:
        """
        创建目录（如果不存在）
        
        Args:
            dir_path: 目录路径
        """
        if dir_path:  # 避免空路径
            os.makedirs(dir_path, exist_ok=True)
    
    @staticmethod
    def get_files_by_pattern(directory: str, pattern: str) -> List[str]:
        """
        根据模式获取文件列表
        
        Args:
            directory: 目录路径
            pattern: 文件模式（如 *.txt）
            
        Returns:
            文件路径列表（已排序）
        """
        if not os.path.exists(directory):
            return []
        
        search_pattern = os.path.join(directory, pattern)
        files = glob.glob(search_pattern)
        return sorted(files)
    
    @staticmethod
    def get_files_by_extension(directory: str, extension: str) -> List[str]:
        """
        根据扩展名获取文件列表
        
        Args:
            directory: 目录路径
            extension: 文件扩展名（如 .txt）
            
        Returns:
            文件路径列表（已排序）
        """
        if not extension.startswith('.'):
            extension = '.' + extension
        
        pattern = f"*{extension}"
        return FileManager.get_files_by_pattern(directory, pattern)
    
    @staticmethod
    def copy_file(src: str, dst: str) -> None:
        """
        复制文件
        
        Args:
            src: 源文件路径
            dst: 目标文件路径
        """
        try:
            FileManager.create_directory(os.path.dirname(dst))
            shutil.copy2(src, dst)
        except Exception as e:
            raise RuntimeError(f"复制文件失败 {src} -> {dst}: {e}")
    
    @staticmethod
    def file_exists(file_path: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件是否存在
        """
        return os.path.exists(file_path) and os.path.isfile(file_path)
    
    @staticmethod
    def get_file_size(file_path: str) -> int:
        """
        获取文件大小
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件大小（字节）
        """
        try:
            return os.path.getsize(file_path)
        except Exception:
            return 0
    
    @staticmethod
    def extract_title_and_body(content: str) -> Tuple[str, str]:
        """
        从内容中提取标题和正文
        
        Args:
            content: 文件内容
            
        Returns:
            (标题, 正文内容)
        """
        lines = content.split('\n')
        
        # 第一行是标题
        title = lines[0].strip() if lines else "Unknown Title"
        
        # 其余是正文（去除开头的空行）
        body_lines = lines[1:]
        while body_lines and not body_lines[0].strip():
            body_lines.pop(0)
        
        body = '\n'.join(body_lines)
        return title, body
    
    @staticmethod
    def get_basename_without_extension(file_path: str) -> str:
        """
        获取不含扩展名的文件名
        
        Args:
            file_path: 文件路径
            
        Returns:
            不含扩展名的文件名
        """
        return os.path.splitext(os.path.basename(file_path))[0]