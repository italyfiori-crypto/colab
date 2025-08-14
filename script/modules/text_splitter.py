#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文本分割模块
使用spaCy进行智能文本分割，保持语义完整性
"""

from typing import List
import sys

try:
    import spacy
except ImportError:
    print("缺少依赖包: spacy")
    print("请安装: pip install spacy")
    print("请下载英文模型: python -m spacy download en_core_web_sm")
    sys.exit(1)


class TextSplitter:
    """智能文本分割器 - 基于spaCy"""
    
    def __init__(self):
        """初始化分割器"""
        try:
            self.nlp = spacy.load("en_core_web_sm")
            print("spaCy英文模型加载成功")
        except OSError:
            print("spaCy英文模型未找到，请运行: python -m spacy download en_core_web_sm")
            sys.exit(1)
    
    def split_text(self, text: str, max_length: int = 120) -> List[str]:
        """
        智能文本分割主函数
        
        Args:
            text: 要分割的文本
            max_length: 每段的最大长度
            
        Returns:
            分割后的文本段列表
        """
        return self._split_with_spacy(text, max_length)
    
    def _split_with_spacy(self, text: str, max_length: int) -> List[str]:
        """
        使用spaCy进行智能文本分割
        
        Args:
            text: 要分割的文本
            max_length: 每段的最大长度
            
        Returns:
            分割后的文本段列表
        """
        # 使用spaCy分析文本
        doc = self.nlp(text)
        
        # 获取句子
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        
        # 将句子组合成适当长度的段落
        segments = []
        current_segment = ""
        
        for sentence in sentences:
            # 如果单个句子超过最大长度，需要进一步分割
            if len(sentence) > max_length:
                # 保存当前段落
                if current_segment:
                    segments.append(current_segment.strip())
                    current_segment = ""
                
                # 分割长句子
                long_segments = self._split_long_sentence(sentence, max_length)
                segments.extend(long_segments)
            else:
                # 检查加上新句子是否会超长
                test_segment = current_segment + (" " if current_segment else "") + sentence
                if len(test_segment) <= max_length:
                    current_segment = test_segment
                else:
                    # 保存当前段落并开始新的
                    if current_segment:
                        segments.append(current_segment.strip())
                    current_segment = sentence
        
        # 添加最后一个段落
        if current_segment:
            segments.append(current_segment.strip())
        
        # 过滤空段落
        return [seg for seg in segments if seg]
    
    def _split_long_sentence(self, sentence: str, max_length: int) -> List[str]:
        """
        分割长句子
        
        Args:
            sentence: 长句子
            max_length: 最大长度
            
        Returns:
            分割后的段落列表
        """
        if not self.nlp:
            return self._split_by_words(sentence, max_length)
        
        # 分析句子结构
        doc = self.nlp(sentence)
        
        # 寻找合适的分割点
        split_points = []
        for token in doc:
            if (token.text in [',', ';', ':', '--', '—'] and 
                token.i < len(doc) - 3):
                split_points.append(token.i + 1)
        
        if not split_points:
            return self._split_by_words(sentence, max_length)
        
        # 根据分割点创建段落
        segments = []
        start = 0
        current_segment = ""
        
        for split_point in split_points:
            segment_text = doc[start:split_point].text.strip()
            
            if len(current_segment + " " + segment_text) <= max_length:
                current_segment += (" " if current_segment else "") + segment_text
            else:
                if current_segment:
                    segments.append(current_segment)
                current_segment = segment_text
            start = split_point
        
        # 处理剩余部分
        if start < len(doc):
            remaining = doc[start:].text.strip()
            if len(current_segment + " " + remaining) <= max_length:
                current_segment += (" " if current_segment else "") + remaining
            else:
                if current_segment:
                    segments.append(current_segment)
                segments.append(remaining)
        else:
            if current_segment:
                segments.append(current_segment)
        
        return segments if segments else [sentence]
    
    def _split_by_words(self, text: str, max_length: int) -> List[str]:
        """按单词强制分割文本"""
        words = text.split()
        segments = []
        current = ""
        
        for word in words:
            if len(current + " " + word) <= max_length:
                current += (" " if current else "") + word
            else:
                if current:
                    segments.append(current)
                current = word
        
        if current:
            segments.append(current)
        
        return segments