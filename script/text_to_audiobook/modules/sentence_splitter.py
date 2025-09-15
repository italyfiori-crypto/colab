#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI句子拆分模块
使用AI智能拆分长句为语义完整的子句
"""

import os
import re
import requests
from typing import List
from dataclasses import dataclass



@dataclass
class SentenceSplitterConfig:
    """AI句子拆分配置类"""
    
    # 输出子目录名
    output_subdir: str = "sentences"
    
    # AI拆分配置
    ai_split_threshold: int = 80  # 触发AI拆分的句子长度阈值
    api_key: str = ""
    model: str = "deepseek-ai/DeepSeek-V2.5"
    base_url: str = "https://api.siliconflow.cn/v1"
    timeout: int = 30
    context_window_size: int = 2  # 提供给AI的上下文句子数量


class AISmartSplitter:
    """AI智能句子拆分器"""
    
    def __init__(self, config: SentenceSplitterConfig):
        """
        初始化AI拆分器
        
        Args:
            config: 句子拆分配置
        """
        self.config = config
        
        if not config.api_key:
            raise RuntimeError("AI拆分器初始化失败: 缺少API密钥")
    
    def split_with_ai(self, sentences: List[str], paragraph_context: str = "") -> List[str]:
        """
        使用AI智能拆分句子列表
        
        Args:
            sentences: 原始句子列表
            paragraph_context: 段落上下文
            
        Returns:
            拆分后的句子列表
        """
        result = []
        
        for i, sentence in enumerate(sentences):
            if len(sentence) < self.config.ai_split_threshold:
                # 短句直接保留
                result.append(sentence)
            else:
                # 长句使用AI拆分
                context_sentences = self._get_context_sentences(sentences, i)
                split_result = self._ai_split_sentence(sentence, context_sentences, paragraph_context)
                result.extend(split_result)
        
        return result
    
    def _get_context_sentences(self, sentences: List[str], current_index: int) -> List[str]:
        """获取当前句子的上下文句子"""
        start = max(0, current_index - self.config.context_window_size)
        end = min(len(sentences), current_index + self.config.context_window_size + 1)
        return sentences[start:end]
    
    def _ai_split_sentence(self, sentence: str, context_sentences: List[str], paragraph_context: str) -> List[str]:
        """
        使用AI拆分单个句子
        
        Args:
            sentence: 要拆分的句子
            context_sentences: 上下文句子
            paragraph_context: 段落上下文
            
        Returns:
            拆分后的句子列表
        """
        try:
            # 构建上下文信息
            context_info = ""
            if context_sentences:
                context_info = f"上下文句子：\n{chr(10).join(context_sentences)}\n\n"
            
            if paragraph_context:
                context_info += f"段落背景：{paragraph_context[:200]}...\n\n"
            
            prompt = f"""请将以下英文长句拆分为多个语义完整的子句。拆分时需要考虑：
1. 保持每个子句的语义完整性
2. 考虑语法结构和逻辑关系
3. 子句长度适中（建议20-60字符）
4. 保持原意不变

{context_info}需要拆分的句子：
{sentence}

请直接返回拆分后的子句，每行一个，不要添加序号或其他格式："""

            response = self._call_api(prompt)
            if not response:
                return [sentence]
            
            result_text = response.strip()
            
            # 解析拆分结果
            split_sentences = []
            for line in result_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('*') and not line.startswith('-'):
                    # 清理可能的序号
                    line = re.sub(r'^\d+\.\s*', '', line)
                    line = re.sub(r'^[•·]\s*', '', line)
                    if line:
                        split_sentences.append(line)
            
            # 如果AI拆分失败，抛出异常
            if not split_sentences:
                raise RuntimeError(f"AI拆分返回空结果: {sentence}")
            
            return split_sentences
            
        except Exception as e:
            print(f"❌ AI拆分失败: {e}")
            raise
    
    def _call_api(self, prompt: str) -> str:
        """
        调用SiliconFlow API
        
        Args:
            prompt: 用户提示词
            
        Returns:
            API响应内容
        """
        try:
            headers = {
                'Authorization': f'Bearer {self.config.api_key}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'model': self.config.model,
                'messages': [
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.1,
                'max_tokens': 1000
            }
            
            response = requests.post(
                f"{self.config.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                print(f"⚠️ API调用失败: {response.status_code} - {response.text}")
                return ""
                
        except Exception as e:
            print(f"⚠️ API调用异常: {e}")
            return ""


class SentenceSplitter:
    """句子拆分器"""
    
    def __init__(self, config: SentenceSplitterConfig):
        """
        初始化AI句子拆分器
        
        Args:
            config: 句子拆分配置
        """
        self.config = config
        self.ai_splitter = AISmartSplitter(config)
    
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
            sentences = self._split_sentences(paragraph, paragraph_context=paragraph)
            
            # 将句子列表转换为字符串（每句一行）
            if sentences:
                paragraph_content = '\n'.join(sentences)
                processed_paragraphs.append(paragraph_content)
        
        # 段落间用空行分隔
        return '\n\n'.join(processed_paragraphs)
    
    def _split_sentences(self, text: str, paragraph_context: str = "") -> List[str]:
        """
        使用AI智能拆分文本为句子
        
        Args:
            text: 输入文本
            paragraph_context: 段落上下文
            
        Returns:
            句子列表
        """
        # 清理文本（移除多余空白）
        text = re.sub(r'\s+', ' ', text.strip())
        
        if not text:
            return []
        
        # 简单的基础句子分割（按句号、感叹号、问号分割）
        sentences = re.split(r'[.!?]+\s+', text)
        # 过滤空句子
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # 使用AI智能拆分
        sentences = self.ai_splitter.split_with_ai(sentences, paragraph_context)
        
        # 清理句子（去除首尾空白）
        sentences = [s.strip() for s in sentences if s.strip()]
        
        return sentences
