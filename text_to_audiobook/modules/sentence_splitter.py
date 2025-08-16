#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
句子拆分模块
将子章节的段落拆分为句子，每个句子占一行，保留段落间隔
使用引号优先的语义感知分割方法
"""

import os
import re
import nltk
import pysbd
from typing import List, Tuple
from dataclasses import dataclass

# 配置：括号类符号（整体保留）
PAIR_SYMBOLS_PARENS = [
    ("(", ")"),
    ("[", "]"),
    ("{", "}"),
    ("（", "）"),
    ("【", "】"),
    ("《", "》"),
]

# 配置：引号类符号（允许内部继续拆分）
PAIR_SYMBOLS_QUOTES = [
    ("“", "”"),
    ('"', '"'),
]

# 配置：句中分隔符（可以再扩展）
SPLIT_PUNCT = [",", "，", ":", "：", ";", "；"]

# 分隔符优先级列表（按语义强度排序）
SEPARATORS = [
    ". ",        # 句号+空格（最高优先级）
    "! ",        # 感叹号+空格
    "? ",        # 问号+空格
    "; ",        # 分号+空格
    ": ",        # 冒号+空格
    ", and ",    # 逗号+and连词
    ", but ",    # 逗号+but连词
    ", or ",     # 逗号+or连词
    ", when ",   # 逗号+when连词
    ", that ",   # 逗号+that连词
    ", ",        # 逗号+空格（最低优先级）
]

# 保护模式（引号、括号等，绝对不拆分）
PROTECTED_PATTERNS = [
    r'"[^"]*"',      # 双引号内容
    r"'[^']*'",      # 单引号内容
    r'\([^)]*\)',    # 圆括号内容
    r'\[[^\]]*\]',   # 方括号内容
]

# 长度控制常量 - 针对语音合成优化
TARGET_MAX_LENGTH = 90      # 目标最大长度（适合语音合成）

MERGE_THRESHOLD = 75        # 合并阈值
MAX_MERGE_LENGTH = 120      # 最大合并长度

# 成对符号定义（支持所有类型引号和括号）
QUOTE_PAIRS = [
    ('"', '"'),     # 标准双引号
    ('"', '"'),     # 弯曲双引号
    ('„', '"'),     # 德式双引号
    ("'", "'"),     # 标准单引号
    ("'", "'"),     # 弯曲单引号
    ("‚", "'"),     # 德式单引号
    ('(', ')'),     # 圆括号
    ('[', ']'),     # 方括号
    ('{', '}'),     # 花括号
]


@dataclass
class SentenceSplitterConfig:
    """句子拆分配置类"""
    
    # 输出子目录名
    output_subdir: str = "sentences"
    
    # 分割器类型：'nltk' 或 'pysbd'
    segmenter: str = "nltk"
    
    # 语言设置
    language: str = "en"
    
    # 是否清理文本
    clean: bool = False
    
    # 是否启用短句拆分
    enable_clause_splitting: bool = True
    
    # 触发拆分的最大句子长度（字符数）
    max_sentence_length: int = 100


class SentenceSplitter:
    """句子拆分器"""
    
    def __init__(self, config: SentenceSplitterConfig):
        """
        初始化句子拆分器
        
        Args:
            config: 句子拆分配置
        """
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
            try:
                # 生成输出文件路径
                filename = os.path.basename(input_file)
                output_file = os.path.join(sentences_dir, filename)
                
                # 处理单个文件
                self._process_file(input_file, output_file)
                output_files.append(output_file)
                
                print(f"📝 已处理句子拆分: {filename}")
            except Exception as e:
                print(f"❌ 拆分失败: {e}")
                continue
        
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
        paragraphs = re.split(r'\n\n', content)
        
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
        将文本拆分为句子，使用引号优先的迭代分割方法
        
        Args:
            text: 输入文本
            
        Returns:
            句子列表
        """
        # 清理文本（移除多余空白）
        text = re.sub(r'\s+', ' ', text.strip())
        
        if not text:
            return []
        
        # 第一阶段：使用专业工具进行基础句子分割
        if self.config.segmenter == "pysbd":
            sentences = self._split_with_pysbd(text)
        else:
            sentences = self._split_with_nltk(text)
        
        # 第二阶段：新的长句拆分逻辑
        if self.config.enable_clause_splitting:
            sentences = self._split_long_sentences_new(sentences)
        
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
    
    
    def _split_long_sentences_new(self, sentences: List[str]) -> List[str]:
        """
        新的长句拆分策略：成对符号保护 + 分隔符拆分 + 智能合并
        
        Args:
            sentences: 原始句子列表
            
        Returns:
            处理后的句子列表
        """
        result = []
        
        for sentence in sentences:
            if len(sentence) <= TARGET_MAX_LENGTH:
                result.append(sentence)
                continue
            
            # 对长句进行拆分-合并处理
            split_result = self.split_into_clauses(sentence)
            result.extend(split_result)
        
        return result
    
    def split_into_clauses(self, text: str,
                        paren_symbols=PAIR_SYMBOLS_PARENS,
                        quote_symbols=PAIR_SYMBOLS_QUOTES,
                        split_punct=SPLIT_PUNCT,
                        min_len: int = 15):
        """
        将文本拆分成子句：
        1. 括号类符号内的文本作为独立子句。
        2. 引号类符号内的文本作为独立子句。
        3. 分隔符触发拆分，分隔符保留在子句末尾。
        4. 短子句自动与前一个子句合并。
        """
        clauses = []
        buf = []
        stack = []  # 跟踪括号/引号状态
        paren_content = []  # 存储括号内内容
        quote_content = []  # 存储引号内内容

        open_parens = {o: c for o, c in paren_symbols}
        close_parens = {c: o for o, c in paren_symbols}
        open_quotes = {o: c for o, c in quote_symbols}
        close_quotes = {c: o for o, c in quote_symbols}

        for ch in text:
            # 括号处理
            if ch in open_parens:
                # 保存当前缓冲区内容作为子句
                if buf:
                    clause = ''.join(buf).strip()
                    if clause:
                        clauses.append(clause)
                    buf = []
                
                stack.append(("paren", ch))
                paren_content = [ch]  # 开始收集括号内内容
                continue
            elif ch in close_parens:
                if stack and stack[-1][1] == close_parens[ch]:
                    stack.pop()
                    # 完成括号内容收集，作为独立子句
                    paren_content.append(ch)
                    clause = ''.join(paren_content).strip()
                    if clause:
                        clauses.append(clause)
                    paren_content = []
                continue

            # 引号处理
            if ch in open_quotes:
                # 保存当前缓冲区内容作为子句
                if buf:
                    clause = ''.join(buf).strip()
                    if clause:
                        clauses.append(clause)
                    buf = []
                
                if not stack or stack[-1][0] != "quote":
                    stack.append(("quote", ch))
                    quote_content = [ch]  # 开始收集引号内内容
                else:
                    stack.pop()
                    # 完成引号内容收集，作为独立子句
                    quote_content.append(ch)
                    clause = ''.join(quote_content).strip()
                    if clause:
                        clauses.append(clause)
                    quote_content = []
                continue

            # 如果在括号或引号内，收集内容
            if paren_content:
                paren_content.append(ch)
                continue
            elif quote_content:
                quote_content.append(ch)
                continue

            # 正常字符处理
            buf.append(ch)

            # 分隔符处理
            if ch in split_punct:
                clause = ''.join(buf).strip()
                if clause:
                    clauses.append(clause)
                buf = []
                continue

        # 收尾
        if buf:
            clause = ''.join(buf).strip()
            if clause:
                clauses.append(clause)

        # 合并过短的子句
        merged = []
        for c in clauses:
            if merged and len(merged[-1]) + len(c) < MAX_MERGE_LENGTH:
                print(f"***合并子句***: {merged[-1]} 和 {c}")
                merged[-1] += " " + c
            else:
                merged.append(c)

        return merged
