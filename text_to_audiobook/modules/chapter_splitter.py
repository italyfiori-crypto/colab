#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
章节拆分模块
支持配置化的多行章节检测和拆分
"""

import re
import os
import json
from typing import List
from dataclasses import dataclass
from .sub_chapter_splitter import SubChapterConfig
from .sentence_splitter import SentenceSplitterConfig


@dataclass
class ChapterPattern:
    """章节模式配置类"""
    
    # 模式名称
    name: str
    
    # 多行正则表达式
    multiline_regex: str
    
    # 标题行索引（0开始）
    title_line_index: int
    
    # 内容开始行偏移
    content_start_offset: int


@dataclass
class ChapterDetectionConfig:
    """章节检测配置类"""
    
    # 章节模式列表
    chapter_patterns: List[ChapterPattern]
    
    # 是否忽略大小写
    ignore_case: bool
    
    # 子章节配置
    sub_chapter: SubChapterConfig
    
    # 句子拆分配置
    sentence: SentenceSplitterConfig
    
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
        
        # 处理章节模式配置
        if 'chapter_patterns' in config_data:
            patterns_data = config_data.pop('chapter_patterns')
            patterns = [ChapterPattern(**pattern_data) for pattern_data in patterns_data]
            config_data['chapter_patterns'] = patterns
        
        # 处理子章节配置
        if 'sub_chapter' in config_data:
            sub_config_data = config_data.pop('sub_chapter')
            sub_config = SubChapterConfig(**sub_config_data)
            config_data['sub_chapter'] = sub_config
        
        # 处理句子拆分配置
        if 'sentence' in config_data:
            sentence_config_data = config_data.pop('sentence')
            sentence_config = SentenceSplitterConfig(**sentence_config_data)
            config_data['sentence'] = sentence_config
        
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
        flags = re.MULTILINE | re.DOTALL
        if self.config.ignore_case:
            flags |= re.IGNORECASE
        
        # 编译所有章节模式
        self.compiled_patterns = []
        for pattern in self.config.chapter_patterns:
            compiled_regex = re.compile(pattern.multiline_regex, flags)
            self.compiled_patterns.append((pattern, compiled_regex))
    
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
            content = f.read()
        
        # 检测章节边界
        chapter_matches = self._detect_chapters(content)
        
        if not chapter_matches:
            raise ValueError(f"未在文件 {input_file} 中检测到任何章节")
        
        # 自动生成子目录名称
        if not subdir_name:
            subdir_name = f"chapters"
        
        # 创建输出目录
        full_output_dir = os.path.join(output_dir, subdir_name)
        os.makedirs(full_output_dir, exist_ok=True)
        
        # 拆分并保存章节
        output_files = []
        for i, chapter_match in enumerate(chapter_matches):
            chapter_title = chapter_match['title']
            chapter_content = chapter_match['content']
            
            # 生成文件名
            filename = self._generate_filename(i + 1, chapter_title)
            file_path = os.path.join(full_output_dir, filename)
            
            # 格式化章节内容
            formatted_content = f"{chapter_title}\n\n{chapter_content}"
            
            # 保存文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(formatted_content)
            
            output_files.append(file_path)
            print(f"已生成章节文件: {file_path}")
        
        print(f"\n成功拆分 {len(output_files)} 个章节到目录: {full_output_dir}")
        
        return output_files
    
    def _detect_chapters(self, content: str) -> List[dict]:
        """
        检测文本中的章节
        
        Args:
            content: 完整文本内容
            
        Returns:
            章节匹配列表，每个元素包含 {'title': str, 'content': str, 'start': int, 'end': int}
        """
        # 尝试所有配置的模式
        for pattern, regex in self.compiled_patterns:
            matches = list(regex.finditer(content))
            if matches:
                print(f"使用模式 '{pattern.name}' 找到 {len(matches)} 个章节")
                return self._extract_chapters_from_matches(content, matches, pattern)
        
        return []
    
    def _extract_chapters_from_matches(self, content: str, matches: List[re.Match], pattern: ChapterPattern) -> List[dict]:
        """
        从正则匹配结果提取章节信息
        
        Args:
            content: 完整文本内容
            matches: 正则匹配结果列表
            pattern: 使用的章节模式
            
        Returns:
            章节信息列表
        """
        chapters = []
        
        for i, match in enumerate(matches):
            # 提取标题
            match_lines = match.group(0).split('\n')
            if pattern.title_line_index < len(match_lines):
                title = match_lines[pattern.title_line_index].strip()
            else:
                title = f"Chapter {i + 1}"
            
            # 计算内容开始位置
            content_start = match.end()
            
            # 计算内容结束位置
            if i < len(matches) - 1:
                content_end = matches[i + 1].start()
            else:
                content_end = len(content)
            
            # 提取原始内容
            raw_content = content[content_start:content_end].strip()
            
            # 处理段落合并
            content_lines = raw_content.split('\n')
            
            # 清理内容（去除开头和结尾的空行）
            while content_lines and not content_lines[0].strip():
                content_lines.pop(0)
            while content_lines and not content_lines[-1].strip():
                content_lines.pop()
            
            # 合并段落（将多行合并为单行）
            processed_lines = self._merge_paragraph_lines(content_lines)
            chapter_content = ''.join(processed_lines).strip()
            
            chapters.append({
                'title': title,
                'content': chapter_content,
                'start': match.start(),
                'end': content_end
            })
        
        return chapters
    
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


