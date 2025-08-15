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
    
    def __init__(self, max_chapter_length: int = 5000, min_split_length: int = 1000):
        """
        初始化预处理器
        
        Args:
            max_chapter_length: 单个子章节最大长度（字符数）
            min_split_length: 最小拆分长度，避免生成过短的章节
        """
        self.max_chapter_length = max_chapter_length
        self.min_split_length = min_split_length
    
    def extract_book_info(self, text: str) -> Dict[str, str]:
        """
        从古腾堡项目文本头部提取书名和作者信息
        
        Args:
            text: 原始文本内容
            
        Returns:
            包含书名和作者的字典 {'title': str, 'author': str}
        """
        lines = text.split('\n')
        book_info = {'title': '', 'author': ''}
        
        # 查找书名和作者信息的范围（头部50行内）
        header_lines = lines[:50]
        
        # 寻找书名 - 在START标记后，author标记前
        start_found = False
        title_candidates = []
        
        for line in header_lines:
            line = line.strip()
            
            # 找到START标记
            if "START OF THE PROJECT GUTENBERG" in line.upper():
                start_found = True
                continue
            
            if start_found and line:
                # 跳过插图标记
                if line.startswith('[Illustration'):
                    continue
                
                # 找到作者信息，停止收集标题
                if line.lower().startswith('by '):
                    # 提取作者名
                    book_info['author'] = line[3:].strip()
                    break
                
                # 跳过空行、星号、版权信息等
                if (not line or 
                    line.startswith('***') or 
                    'copyright' in line.lower() or
                    'dedicated' in line.lower() or
                    'edition' in line.lower() or
                    len(line) < 3):
                    continue
                
                # 收集潜在的标题行
                if len(line) > 3 and not line.isdigit():
                    title_candidates.append(line)
        
        # 处理标题候选项，选择最合适的作为书名
        if title_candidates:
            # 优先选择较长且格式化的标题
            best_title = max(title_candidates, key=lambda x: (len(x), x.istitle()))
            book_info['title'] = best_title
        
        return book_info
    
    def preprocess_text(self, text: str) -> List[Dict[str, str]]:
        """
        预处理文本：删除头部信息、目录，按章节分割，并智能拆分长章节
        
        Args:
            text: 原始文本内容
            
        Returns:
            章节列表，每个元素包含 {'title': str, 'content': str, ...}
            长章节会被拆分为多个子章节，包含完整的元信息
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
        
        # 智能拆分过长的章节
        all_chapters = []
        for i, chapter in enumerate(chapters):
            sub_chapters = self._split_long_chapter(chapter, i)
            all_chapters.extend(sub_chapters)
            
            # 打印拆分信息
            if len(sub_chapters) > 1:
                print(f"章节 '{chapter['title']}' 长度 {len(chapter['content'])} 字符，拆分为 {len(sub_chapters)} 个子章节")
        
        return all_chapters
    
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
    
    def _find_best_split_point(self, text: str, target_length: int) -> int:
        """
        在指定位置附近找到最佳的文本拆分点，优先选择段落边界
        
        Args:
            text: 要拆分的文本
            target_length: 目标拆分长度
            
        Returns:
            最佳拆分位置的索引
        """
        if len(text) <= target_length:
            return len(text)
        
        # 搜索范围：目标长度前后25%，给段落边界更多搜索空间
        search_start = max(int(target_length * 0.75), self.min_split_length)
        search_end = min(int(target_length * 1.25), len(text))
        
        # 优先级拆分点（按优先级排序，段落边界优先）
        split_patterns = [
            # 第一优先级：段落边界
            r'\n\n+',               # 空行（段落分隔），最佳拆分点
            r'\n\s*[A-Z]',          # 换行后跟大写字母（新段落开始）
            r'\.\s*\n',             # 句号后换行（段落结束）
            r'\!\s*\n',             # 感叹号后换行
            r'\?\s*\n',             # 问号后换行
            
            # 第二优先级：句子边界
            r'\.\s+[A-Z]',          # 句号后跟大写字母（新句子开始）
            r'\!\s+[A-Z]',          # 感叹号后跟大写字母
            r'\?\s+[A-Z]',          # 问号后跟大写字母
            
            # 第三优先级：标点符号后
            r'\.\s',                # 句号后有空格
            r'\!\s',                # 感叹号后有空格
            r'\?\s',                # 问号后有空格
            r';\s',                 # 分号后有空格
            r':\s',                 # 冒号后有空格
            r',\s',                 # 逗号后有空格
        ]
        
        # 在搜索范围内寻找最佳拆分点
        for priority, pattern in enumerate(split_patterns):
            matches = []
            for match in re.finditer(pattern, text[search_start:search_end]):
                pos = search_start + match.end()
                # 对于段落边界，给予额外的权重
                weight = 1.0
                if priority < 5:  # 段落边界和句子边界
                    weight = 0.7  # 优先选择接近目标长度的段落边界
                
                matches.append((pos, abs(pos - target_length) * weight))
            
            if matches:
                # 选择加权距离最小的匹配点
                best_match = min(matches, key=lambda x: x[1])[0]
                return best_match
        
        # 如果没有找到合适的标点拆分点，寻找单词边界
        for i in range(min(target_length + 200, len(text)), search_start - 1, -1):
            if text[i].isspace():
                return i + 1
        
        # 最后的选择：强制在目标长度拆分
        return min(target_length, len(text))
    
    def _split_long_chapter(self, chapter: Dict[str, str], chapter_index: int) -> List[Dict[str, str]]:
        """
        拆分过长的章节为多个子章节，实现近似平均拆分，保留完整元信息
        
        Args:
            chapter: 原始章节数据 {'title': str, 'content': str}
            chapter_index: 章节索引（用于生成子章节编号）
            
        Returns:
            拆分后的子章节列表
        """
        content = chapter['content']
        title = chapter['title']
        
        # 如果章节不够长，不需要拆分
        if len(content) <= self.max_chapter_length:
            return [chapter]
        
        # 计算理想的子章节数量，确保每个子章节都在合理范围内
        total_length = len(content)
        min_parts = max(2, (total_length + self.max_chapter_length - 1) // self.max_chapter_length)
        max_parts = total_length // self.min_split_length
        
        # 选择最优的子章节数量，使长度分布最均匀
        best_parts = min_parts
        best_variance = float('inf')
        
        for parts in range(min_parts, min(max_parts + 1, min_parts + 3)):
            avg_length = total_length / parts
            if avg_length >= self.min_split_length and avg_length <= self.max_chapter_length:
                # 计算长度分布的方差
                variance = abs(avg_length - (self.min_split_length + self.max_chapter_length) / 2)
                if variance < best_variance:
                    best_variance = variance
                    best_parts = parts
        
        # 执行智能平均拆分
        sub_chapters = []
        current_pos = 0
        
        for sub_index in range(1, best_parts + 1):
            remaining_text = content[current_pos:]
            remaining_parts = best_parts - sub_index + 1
            
            if remaining_parts == 1:
                # 最后一个子章节，包含所有剩余内容
                sub_content = remaining_text
            else:
                # 计算当前子章节的理想长度
                remaining_length = len(remaining_text)
                ideal_length = remaining_length // remaining_parts
                
                # 在合理范围内调整目标长度
                target_length = max(
                    self.min_split_length,
                    min(ideal_length, self.max_chapter_length)
                )
                
                # 找到最佳拆分点（优先段落边界）
                split_point = self._find_best_split_point(remaining_text, target_length)
                sub_content = remaining_text[:split_point].strip()
                
                # 防止子章节过短，如果太短则扩展
                if len(sub_content) < self.min_split_length and remaining_parts > 1:
                    extended_target = max(self.min_split_length * 1.2, target_length * 1.1)
                    split_point = self._find_best_split_point(remaining_text, extended_target)
                    sub_content = remaining_text[:split_point].strip()
            
            # 创建子章节
            sub_chapter = {
                'title': f"{title} - 第{sub_index}部分",
                'content': sub_content,
                'parent_chapter': chapter_index + 1,
                'sub_chapter_index': sub_index,
                'is_sub_chapter': True,
                'original_title': title,
                'total_sub_chapters': best_parts
            }
            sub_chapters.append(sub_chapter)
            
            # 移动到下一个位置
            if sub_index < best_parts:
                if 'split_point' in locals():
                    current_pos += split_point
                    # 跳过可能的空白字符
                    while current_pos < len(content) and content[current_pos].isspace():
                        current_pos += 1
                else:
                    break
            
            # 防止无限循环
            if current_pos >= len(content):
                break
        
        return sub_chapters