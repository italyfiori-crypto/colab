#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本预处理模块
负责古腾堡文本的头部清理、章节识别和内容清理
"""

import re
from typing import List, Dict


class TextProcessor:
    """文本预处理器"""
    
    def __init__(self):
        """初始化预处理器"""
        pass
    
    def preprocess_text(self, text: str) -> List[Dict[str, str]]:
        """
        预处理文本：删除头部信息、目录，按章节分割
        
        Args:
            text: 原始文本内容
            
        Returns:
            章节列表，每个元素包含 {'title': str, 'content': str}
        """
        lines = text.split('\n')
        
        # 删除古腾堡项目头部信息
        content_start = self._find_content_start(lines)
        content_lines = lines[content_start:]
        
        # 按章节分割
        chapters = self._split_into_chapters(content_lines)
        
        # 清理章节内容
        for chapter in chapters:
            chapter["content"] = self._clean_content(chapter["content"])
        
        return chapters
    
    def _find_content_start(self, lines: List[str]) -> int:
        """查找正文开始位置"""
        content_start = 0
        
        # 查找第一章开始
        for i, line in enumerate(lines):
            if "CHAPTER I" in line.upper() or "第一章" in line or line.strip().startswith("1."):
                content_start = i
                break
        
        # 如果没有找到明确的开始标记，删除前30行的标准头部
        if content_start == 0:
            for i, line in enumerate(lines[:50]):
                if line.strip() and not any(marker in line.upper() for marker in 
                    ["PROJECT GUTENBERG", "START OF", "CONTENTS", "目录", "ILLUSTRATION", "***"]):
                    content_start = i
                    break
        
        return content_start
    
    def _split_into_chapters(self, content_lines: List[str]) -> List[Dict[str, str]]:
        """按章节分割文本"""
        chapters = []
        current_chapter = {"title": "开始", "content": ""}
        
        for line in content_lines:
            line = line.strip()
            
            # 识别章节标题
            if self._is_chapter_title(line):
                # 保存上一章节
                if current_chapter["content"].strip():
                    chapters.append(current_chapter)
                
                # 开始新章节
                current_chapter = {
                    "title": line,
                    "content": ""
                }
            else:
                # 添加到当前章节内容
                if line:
                    current_chapter["content"] += line + " "
        
        # 添加最后一个章节
        if current_chapter["content"].strip():
            chapters.append(current_chapter)
        
        return chapters
    
    def _is_chapter_title(self, line: str) -> bool:
        """判断是否为章节标题"""
        line_upper = line.upper().strip()
        if not line_upper:
            return False
            
        # 章节标题模式
        title_patterns = [
            r'^CHAPTER\s+[IVX\d]+',           # CHAPTER I, CHAPTER 1
            r'^第.+章',                      # 中文章节
            r'^PART\s+[IVX\d]+',             # PART I
            r'^\d+\.',                       # 1. 2. 3.
            r'^BOOK\s+[IVX\d]+',             # BOOK I
        ]
        
        # 检查章节标题
        for pattern in title_patterns:
            if re.match(pattern, line_upper):
                return True
                
        # 检查章节描述（如"Down the Rabbit-Hole"）
        if len(line_upper) <= 50:  # 标题通常较短
            description_patterns = [
                r'^[A-Z][A-Z\s\-]+$',            # 全大写短语
                r'^[A-Z][a-z]+(\s+the\s+[A-Z][a-z\-]+)+$',  # "Down the Rabbit-Hole"格式
            ]
            
            for pattern in description_patterns:
                if re.match(pattern, line_upper):
                    # 排除常见正文词汇
                    common_words = ['WAS', 'WERE', 'HAD', 'HAVE', 'SAID', 'THOUGHT']
                    if not any(word in line_upper.split() for word in common_words):
                        return True
        
        return False
    
    def _clean_content(self, content: str) -> str:
        """清理文本内容"""
        # 删除多余空白
        content = re.sub(r'\s+', ' ', content)
        
        # 删除格式标记
        content = re.sub(r'\[Illustration.*?\]', '', content)
        content = re.sub(r'\*{3,}.*?\*{3,}', '', content)
        
        # 规范化标点符号
        content = content.replace('"', '"').replace('"', '"')
        content = content.replace(''', "'").replace(''', "'")
        
        return content.strip()
    
    def filter_chapter_titles(self, content: str, chapter_title: str) -> str:
        """过滤章节标题和描述"""
        # 按句子分割内容
        parts = re.split(r'[.!?]+\s*', content)
        filtered_parts = []
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # 跳过章节标题
            if self._is_chapter_title(part):
                continue
                
            # 跳过与章节标题相同的内容
            if part.upper() == chapter_title.upper():
                continue
                
            # 跳过太短的片段
            if len(part) < 10:
                continue
                
            filtered_parts.append(part)
        
        # 重新组合内容
        result = '. '.join(filtered_parts)
        if result and not result.endswith('.'):
            result += '.'
            
        return result