#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
句子拆分模块
将子章节的段落拆分为句子，每个句子占一行，保留段落间隔
"""

import os
import re
import nltk
import pysbd
from typing import List
from dataclasses import dataclass


@dataclass
class SentenceSplitterConfig:
    """句子拆分配置类"""
    
    # 输出子目录名
    output_subdir: str = "sentences"
    
    # 分割器类型：'nltk' 或 'pysbd'
    segmenter: str = "pysbd"
    
    # 语言设置
    language: str = "en"
    
    # 是否清理文本
    clean: bool = False


class SentenceSplitter:
    """句子拆分器"""
    
    def __init__(self, config: SentenceSplitterConfig):
        """
        初始化句子拆分器
        
        Args:
            config: 句子拆分配置
        """
        nltk.download('punkt_tab')
        self.config = config
        self._ensure_nltk_data()
    
    def _ensure_nltk_data(self):
        """
        确保NLTK数据包可用
        """
        try:
            nltk.data.find('tokenizers/punkt')
        except LookupError:
            print("下载NLTK punkt数据包...")
            nltk.download('punkt')
    
    def split_files(self, input_files: List[str], output_dir: str) -> List[str]:
        """
        拆分文件列表为句子级文件
        
        Args:
            input_files: 输入文件路径列表
            output_dir: 输出目录
            
        Returns:
            生成的句子文件路径列表
        """
        # 创建输出目录
        sentences_dir = os.path.join(output_dir, self.config.output_subdir)
        os.makedirs(sentences_dir, exist_ok=True)
        
        output_files = []
        
        for input_file in input_files:
            # 生成输出文件路径
            filename = os.path.basename(input_file)
            output_file = os.path.join(sentences_dir, filename)
            
            # 处理单个文件
            self._process_file(input_file, output_file)
            output_files.append(output_file)
            
            print(f"📝 已处理句子拆分: {filename}")
        
        print(f"\n📁 句子拆分完成，输出到: {sentences_dir}")
        return output_files
    
    def _process_file(self, input_file: str, output_file: str):
        """
        处理单个文件的句子拆分
        
        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径
        """
        # 读取输入文件
        with open(input_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取标题和正文
        title, body = self._extract_title_and_body(content)
        
        # 处理段落句子拆分
        processed_content = self._split_paragraphs_to_sentences(body)
        
        # 构建最终内容
        final_content = f"{title}\n\n{processed_content}"
        
        # 写入输出文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(final_content)
    
    def _extract_title_and_body(self, content: str) -> tuple[str, str]:
        """
        提取标题和正文内容
        
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
    
    def _split_paragraphs_to_sentences(self, content: str) -> str:
        """
        将内容按段落拆分，再将每个段落拆分为句子
        
        Args:
            content: 正文内容
            
        Returns:
            处理后的内容
        """
        # 按段落分割（双换行分割）
        paragraphs = re.split(r'\n\s*\n', content)
        
        # 过滤空段落
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        processed_paragraphs = []
        
        for paragraph in paragraphs:
            # 对段落进行句子拆分
            sentences = self._split_sentences(paragraph)
            
            # 将句子列表转换为字符串（每句一行）
            if sentences:
                paragraph_content = '\n'.join(sentences)
                processed_paragraphs.append(paragraph_content)
        
        # 段落间用空行分隔
        return '\n\n'.join(processed_paragraphs)
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        将文本拆分为句子，支持多种分割器
        
        Args:
            text: 输入文本
            
        Returns:
            句子列表
        """
        # 清理文本（移除多余空白）
        text = re.sub(r'\s+', ' ', text.strip())
        
        if not text:
            return []
        
        # 根据配置选择分割器
        if self.config.segmenter == "pysbd":
            sentences = self._split_with_pysbd(text)
        else:
            sentences = self._split_with_nltk(text)
        
        # 后处理：合并引号内的句子
        sentences = self._merge_quoted_sentences(sentences)
        
        # 清理句子（去除首尾空白）
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
    
    def _split_with_pysbd(self, text: str) -> List[str]:
        """
        使用pySBD进行句子分割
        
        Args:
            text: 输入文本
            
        Returns:
            句子列表
        """
        seg = pysbd.Segmenter(language=self.config.language, clean=self.config.clean)
        return seg.segment(text)
    
    def _split_with_nltk(self, text: str) -> List[str]:
        """
        使用NLTK进行句子分割
        
        Args:
            text: 输入文本
            
        Returns:
            句子列表
        """
        return nltk.sent_tokenize(text)
    
    def _merge_quoted_sentences(self, sentences: List[str]) -> List[str]:
        """
        合并引号内被错误拆分的句子
        
        Args:
            sentences: 原始句子列表
            
        Returns:
            合并后的句子列表
        """
        if not sentences:
            return sentences
        
        merged = []
        current_sentence = ""
        in_quote = False
        
        for sentence in sentences:
            # 清理句子中的转义字符
            clean_sentence = sentence.replace('\\!', '!').replace('\\"', '"')
            
            # 检查是否包含引号
            quote_count = clean_sentence.count('"')
            
            if not in_quote:
                # 不在引号内
                if quote_count % 2 == 1:
                    # 开始引号
                    in_quote = True
                    current_sentence = clean_sentence
                else:
                    # 完整句子
                    merged.append(clean_sentence)
            else:
                # 在引号内
                current_sentence += " " + clean_sentence
                if quote_count % 2 == 1:
                    # 结束引号
                    in_quote = False
                    merged.append(current_sentence)
                    current_sentence = ""
        
        # 处理未闭合的引号
        if current_sentence:
            merged.append(current_sentence)
        
        return merged