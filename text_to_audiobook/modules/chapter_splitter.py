#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
章节拆分模块
支持配置化的多行章节检测和拆分
"""

import re
import os
import json
from typing import List, Tuple, Optional
from dataclasses import dataclass
from .sub_chapter_splitter import SubChapterConfig


@dataclass
class ChapterDetectionConfig:
    """章节检测配置类"""
    
    # 章节标识行正则表达式
    chapter_pattern: str
    
    # 标题行正则表达式（可选，用于验证标题格式）
    title_pattern: Optional[str]
    
    # 标题行相对于章节标识行的偏移量
    title_line_offset: int
    
    # 是否跳过空行寻找标题
    skip_empty_lines: bool
    
    # 最大搜索标题的行数
    max_title_search_lines: int
    
    # 章节头部总行数（用于跳过到内容开始）
    header_lines_count: int
    
    # 是否忽略大小写
    ignore_case: bool
    
    # 子章节配置
    sub_chapter: SubChapterConfig
    
    @classmethod
    def from_json_file(cls, config_path: str) -> 'ChapterDetectionConfig':
        """
        从JSON配置文件加载配置
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            配置对象
        """
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        # 处理子章节配置
        if 'sub_chapter' in config_data:
            sub_config_data = config_data.pop('sub_chapter')
            sub_config = SubChapterConfig(**sub_config_data)
            config_data['sub_chapter'] = sub_config
        
        return cls(**config_data)
    


class ChapterSplitter:
    """章节拆分器"""
    
    def __init__(self, config: ChapterDetectionConfig):
        """
        初始化章节拆分器
        
        Args:
            config: 章节检测配置
        """
        self.config = config
        
        # 编译正则表达式
        flags = re.IGNORECASE if self.config.ignore_case else 0
        self.chapter_regex = re.compile(self.config.chapter_pattern, flags)
        
        if self.config.title_pattern:
            self.title_regex = re.compile(self.config.title_pattern, flags)
        else:
            self.title_regex = None
    
    def split_book(self, input_file: str, output_dir: str = "./output", subdir_name: str = None) -> List[str]:
        """
        拆分书籍为章节文件
        
        Args:
            input_file: 输入文件路径
            output_dir: 输出目录
            subdir_name: 子目录名称，如果为None则自动生成
            
        Returns:
            生成的章节文件路径列表
        """
        # 读取输入文件
        with open(input_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # 检测章节边界
        chapter_boundaries = self._detect_chapter_boundaries(lines)
        
        if not chapter_boundaries:
            raise ValueError(f"未在文件 {input_file} 中检测到任何章节")
        
        # 自动生成子目录名称
        if not subdir_name:
            subdir_name = f"chapters"
        
        # 创建输出目录
        full_output_dir = os.path.join(output_dir, subdir_name)
        os.makedirs(full_output_dir, exist_ok=True)
        
        # 拆分并保存章节
        output_files = []
        for i, (start_line, end_line, chapter_info) in enumerate(chapter_boundaries):
            chapter_num, chapter_title = chapter_info
            
            # 生成文件名
            filename = self._generate_filename(i + 1, chapter_title)
            file_path = os.path.join(full_output_dir, filename)
            
            # 提取章节内容
            chapter_content = self._extract_chapter_content(lines, start_line, end_line, chapter_title)
            
            # 保存文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(chapter_content)
            
            output_files.append(file_path)
            print(f"已生成章节文件: {file_path}")
        
        print(f"\n成功拆分 {len(output_files)} 个章节到目录: {full_output_dir}")
        
        return output_files
    
    def _detect_chapter_boundaries(self, lines: List[str]) -> List[Tuple[int, int, Tuple[str, str]]]:
        """
        检测章节边界
        
        Args:
            lines: 文件行列表
            
        Returns:
            章节边界列表，每个元素为 (开始行号, 结束行号, (章节号, 章节标题))
        """
        chapter_starts = []
        
        # 首先找到所有章节开始位置
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # 检测章节标识行
            if self.chapter_regex.match(line_stripped):
                # 提取章节信息
                chapter_info = self._extract_chapter_info(lines, i)
                if chapter_info:
                    # 记录章节标识行位置和内容开始位置
                    content_start = self._find_content_start(lines, i)
                    chapter_starts.append((i, content_start, chapter_info))
        
        # 构建章节边界
        boundaries = []
        for i, (chapter_line, content_start, chapter_info) in enumerate(chapter_starts):
            if i < len(chapter_starts) - 1:
                # 当前章节结束于下一章节标识行之前
                next_chapter_line = chapter_starts[i + 1][0]
                end_line = next_chapter_line - 1
            else:
                # 最后一章节到文件结尾
                end_line = len(lines) - 1
            
            boundaries.append((content_start, end_line, chapter_info))
        
        return boundaries
    
    def _extract_chapter_info(self, lines: List[str], chapter_line_idx: int) -> Optional[Tuple[str, str]]:
        """
        提取章节号和标题
        
        Args:
            lines: 文件行列表
            chapter_line_idx: 章节标识行索引
            
        Returns:
            (章节号, 章节标题) 或 None
        """
        chapter_line = lines[chapter_line_idx].strip()
        
        # 提取章节号
        chapter_match = self.chapter_regex.match(chapter_line)
        if not chapter_match:
            return None
        
        chapter_num = chapter_line
        
        # 寻找标题行
        title = self._find_title_line(lines, chapter_line_idx)
        if not title:
            title = f"Unknown Title {chapter_line_idx + 1}"
        
        return (chapter_num, title)
    
    def _find_title_line(self, lines: List[str], chapter_line_idx: int) -> Optional[str]:
        """
        寻找章节标题行
        
        Args:
            lines: 文件行列表
            chapter_line_idx: 章节标识行索引
            
        Returns:
            章节标题或None
        """
        search_start = chapter_line_idx + self.config.title_line_offset
        search_end = min(
            chapter_line_idx + self.config.max_title_search_lines + 1,
            len(lines)
        )
        
        for i in range(search_start, search_end):
            if i >= len(lines):
                break
            
            line = lines[i].strip()
            
            # 跳过空行（如果配置允许）
            if self.config.skip_empty_lines and not line:
                continue
            
            # 找到非空行
            if line:
                # 如果有标题正则，验证格式
                if self.title_regex and not self.title_regex.match(line):
                    continue
                
                return line
        
        return None
    
    def _find_content_start(self, lines: List[str], chapter_line_idx: int) -> int:
        """
        找到章节内容开始行号
        
        Args:
            lines: 文件行列表
            chapter_line_idx: 章节标识行索引
            
        Returns:
            内容开始行号
        """
        # 简单策略：跳过固定行数
        content_start = chapter_line_idx + self.config.header_lines_count
        
        # 确保不超过文件范围
        return min(content_start, len(lines))
    
    def _extract_chapter_content(self, lines: List[str], start_line: int, end_line: int, chapter_title: str) -> str:
        """
        提取章节内容
        
        Args:
            lines: 文件行列表
            start_line: 开始行号
            end_line: 结束行号
            chapter_title: 章节标题
            
        Returns:
            格式化的章节内容
        """
        # 提取内容行
        content_lines = lines[start_line:end_line + 1]
        
        # 清理内容（去除开头和结尾的空行）
        while content_lines and not content_lines[0].strip():
            content_lines.pop(0)
        
        while content_lines and not content_lines[-1].strip():
            content_lines.pop()
        
        # 合并段落（将多行合并为单行）
        processed_lines = self._merge_paragraph_lines(content_lines)
        
        # 构建最终内容：第一行是章节标题
        result_lines = [chapter_title + '\n', '\n']
        result_lines.extend(processed_lines)
        
        return ''.join(result_lines)
    
    def _merge_paragraph_lines(self, lines: List[str]) -> List[str]:
        """
        合并段落内的多行为单行
        
        Args:
            lines: 原始行列表
            
        Returns:
            处理后的行列表
        """
        if not lines:
            return []
        
        result = []
        current_paragraph = []
        
        for line in lines:
            line_stripped = line.strip()
            
            if not line_stripped:
                # 空行，表示段落结束
                if current_paragraph:
                    # 合并当前段落
                    merged_line = self._merge_lines(current_paragraph)
                    result.append(merged_line + '\n')
                    current_paragraph = []
                result.append('\n')  # 保留段落间的空行
            else:
                # 非空行，加入当前段落
                current_paragraph.append(line_stripped)
        
        # 处理最后一个段落
        if current_paragraph:
            merged_line = self._merge_lines(current_paragraph)
            result.append(merged_line + '\n')
        
        return result
    
    def _merge_lines(self, lines: List[str]) -> str:
        """
        将多行文本合并为一行
        
        Args:
            lines: 行列表
            
        Returns:
            合并后的单行文本
        """
        if not lines:
            return ""
        
        if len(lines) == 1:
            return lines[0]
        
        result = lines[0]
        
        for i in range(1, len(lines)):
            prev_line = result
            current_line = lines[i].strip()
            
            # 检查前一行是否以标点符号结尾
            if prev_line and prev_line[-1] in '.,;:!?"\'':
                # 有标点符号，直接连接不加空格
                result += current_line
            else:
                # 没有标点符号，加一个空格连接
                result += ' ' + current_line
        
        return result
    
    def _generate_filename(self, chapter_num: int, chapter_title: str) -> str:
        """
        生成章节文件名
        
        Args:
            chapter_num: 章节序号
            chapter_title: 章节标题
            
        Returns:
            文件名
        """
        # 清理标题中的特殊字符
        clean_title = re.sub(r'[^\w\s-]', '', chapter_title)
        clean_title = re.sub(r'\s+', '_', clean_title.strip())
        
        # 限制标题长度
        if len(clean_title) > 50:
            clean_title = clean_title[:50]
        
        return f"{chapter_num:02d}_{clean_title}.txt"


