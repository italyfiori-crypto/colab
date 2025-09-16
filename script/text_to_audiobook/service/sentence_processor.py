#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
句子处理服务 - 负责句子拆分
从子章节文件拆分为句子级别文件
"""

import os
import re
import time
from typing import List
from concurrent.futures import ThreadPoolExecutor, as_completed
from infra import AIClient, FileManager
from infra.config_loader import AppConfig
from util import OUTPUT_DIRECTORIES


class SentenceProcessor:
    """句子处理器 - 负责句子拆分"""
    
    def __init__(self, config: AppConfig):
        """
        初始化句子处理器
        
        Args:
            config: 应用配置
        """
        self.config = config
        self.ai_client = AIClient(config.api)
        self.file_manager = FileManager()
        self.min_paragraph_length = 80  # 最小段落长度阈值
    
    def split_sub_chapters_to_sentences(self, sub_chapter_files: List[str], output_dir: str, force_regenerate: bool = False) -> List[str]:
        """
        将子章节文件拆分为句子文件
        
        Args:
            sub_chapter_files: 子章节文件列表
            output_dir: 输出目录
            force_regenerate: 是否强制重新生成（忽略已存在文件）
            
        Returns:
            句子文件列表
        """
        print(f"🔄 开始AI句子拆分...")
        
        # 创建句子目录
        sentences_dir = os.path.join(output_dir, OUTPUT_DIRECTORIES['sentences'])
        self.file_manager.create_directory(sentences_dir)
        
        sentence_files = []
        processed_count = 0
        skipped_count = 0
        
        for sub_chapter_file in sub_chapter_files:
            filename = os.path.basename(sub_chapter_file)
            sentence_file = os.path.join(sentences_dir, filename)
            
            # 检查文件是否已存在且完整
            if not force_regenerate and self._is_sentence_file_complete(sentence_file, sub_chapter_file):
                sentence_files.append(sentence_file)
                skipped_count += 1
                print(f"⏭️  跳过已存在文件: {filename}")
                continue
            
            try:
                # 处理单个文件
                print(f"📝 开始处理句子拆分: {filename}")
                self._process_sub_chapter_file(sub_chapter_file, sentence_file)
                sentence_files.append(sentence_file)
                processed_count += 1
                print(f"📝 已处理句子拆分: {filename}")
            except Exception as e:
                print(f"❌ 处理失败 {filename}: {e}")
                continue
        
        print(f"\n📊 句子拆分统计:")
        print(f"  ✅ 新处理文件: {processed_count} 个")
        print(f"  ⏭️  跳过已存在: {skipped_count} 个")
        print(f"  📁 输出目录: {sentences_dir}")
        print(f"✅ 句子拆分完成! 总共 {len(sentence_files)} 个句子文件")
        return sentence_files
    
    def _is_sentence_file_complete(self, sentence_file: str, source_file: str) -> bool:
        """
        检查句子文件是否已存在且完整
        
        Args:
            sentence_file: 句子文件路径
            source_file: 源文件路径
            
        Returns:
            是否完整
        """
        if not os.path.exists(sentence_file):
            return False
        
        try:
            # 检查文件大小是否合理（不为空）
            if os.path.getsize(sentence_file) < 10:
                return False
            
            # 检查文件内容格式（应该有标题和内容）
            content = self.file_manager.read_text_file(sentence_file)
            lines = content.split('\n')
            
            # 至少应该有标题行、空行、内容行
            if len(lines) < 3:
                return False
            
            # 检查是否有标题（第一行非空）
            if not lines[0].strip():
                return False
            
            return True
            
        except Exception:
            return False
    
    def _process_sub_chapter_file(self, input_file: str, output_file: str):
        """
        处理单个子章节文件的句子拆分
        
        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径
        """
        # 读取输入文件
        content = self.file_manager.read_text_file(input_file)
        title, body = self.file_manager.extract_title_and_body(content)
        
        # 处理段落句子拆分
        processed_content = self._split_paragraphs_to_sentences(body)
        
        # 构建最终内容
        final_content = f"{title}\n\n{processed_content}"
        
        # 写入输出文件
        self.file_manager.write_text_file(output_file, final_content)
    
    def _split_paragraphs_to_sentences(self, content: str) -> str:
        """
        将段落拆分为句子，使用并发处理
        
        Args:
            content: 段落内容
            
        Returns:
            拆分后的内容
        """
        # 按段落分割
        paragraphs = [p.strip() for p in re.split(r'\n\n', content) if p.strip()]
        
        if not paragraphs:
            return ""
        
        # 分离短段落和长段落
        short_paragraphs = []
        long_paragraphs = []
        
        for i, paragraph in enumerate(paragraphs):
            if len(paragraph) < self.min_paragraph_length:
                short_paragraphs.append((i, paragraph))
            else:
                long_paragraphs.append((i, paragraph))
        
        print(f"🔄 开始段落拆分: 总共{len(paragraphs)}个段落, 跳过{len(short_paragraphs)}个短段落, 并发处理{len(long_paragraphs)}个段落")
        
        # 初始化结果数组
        processed_paragraphs = [None] * len(paragraphs)
        
        # 短段落直接保留
        for i, paragraph in short_paragraphs:
            processed_paragraphs[i] = paragraph
        
        # 并发处理长段落
        if long_paragraphs:
            start_time = time.time()
            max_workers = min(self.config.api.max_concurrent_workers, len(long_paragraphs))
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有长段落到线程池
                future_to_index = {}
                for i, paragraph in long_paragraphs:
                    future = executor.submit(self._split_paragraph_sentences, paragraph)
                    future_to_index[future] = i
                
                # 收集结果并显示进度
                completed_count = 0
                for future in as_completed(future_to_index):
                    index = future_to_index[future]
                    completed_count += 1
                    
                    try:
                        sentences = future.result()
                        if sentences:
                            processed_paragraphs[index] = '\n'.join(sentences)
                        else:
                            processed_paragraphs[index] = paragraphs[index]  # 失败时保留原段落
                        
                        print(f"⚡ 并发处理中... [{completed_count}/{len(long_paragraphs)}] 已完成")
                        
                    except Exception as e:
                        print(f"❌ 段落处理失败: {e}")
                        processed_paragraphs[index] = paragraphs[index]  # 失败时保留原段落
            
            elapsed_time = time.time() - start_time
            print(f"✅ 段落拆分完成: 处理{len(long_paragraphs)}个段落, 耗时{elapsed_time:.2f}秒")
        
        # 过滤None值并合并结果
        result_paragraphs = [p for p in processed_paragraphs if p is not None]
        return '\n\n'.join(result_paragraphs)
    
    def _split_paragraph_sentences(self, paragraph: str) -> List[str]:
        """
        使用AI拆分段落中的句子
        
        Args:
            paragraph: 段落文本
            
        Returns:
            句子列表
        """
        # 清理文本
        text = re.sub(r'\s+', ' ', paragraph.strip())
        if not text:
            return []
        
        # 直接交给AI处理整个段落
        # 让AI智能处理所有分割、引号、缩写等问题
        split_result = self._ai_split_sentence(text, [], paragraph)
        
        return split_result
    
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
        # 构建上下文信息
        context_info = ""
        if context_sentences:
            context_info = f"上下文句子：\n{chr(10).join(context_sentences)}\n\n"
        
        if paragraph_context:
            context_info += f"段落背景：{paragraph_context[:200]}...\n\n"
        
        prompt = f"""请将以下英文长句拆分为多个语义完整的子句。拆分原则：
1. 每个子句语义完整，保留标点符号和连字符
2. 子句长度控制在40-80字符，超过120字符必须拆分
3. 优先在句子完整分隔符处拆分，其次在断点拆分：从句边界、介词短语、并列成分
4. 保持and连接的动作序列完整，保持对话引语连贯

正确示例：
原句：He looked up and saw the bird flying overhead, calling loudly to its mate, "Come here! Come here!" as it circled the tree with great excitement.
拆分：
He looked up and saw the bird flying overhead, calling loudly to its mate,
"Come here! Come here!" as it circled the tree with great excitement.

原句：And when the ducks stood on their heads suddenly, as ducks will, he would dive down and tickle their necks, just under where their chins would be if ducks had chins.
拆分：
And when the ducks stood on their heads suddenly, as ducks will,
he would dive down and tickle their necks,
just under where their chins would be if ducks had chins.

原句: Everyone for what he likes!_We_ like to be Heads down, tails up,Dabbling free!
拆分:
Everyone for what he likes!
_We_ like to be Heads down, tails up, Dabbling free!

{context_info}需要拆分的句子：
{sentence}

请直接返回拆分后的子句，每行一个："""

        try:
            response = self.ai_client.chat_completion(prompt)
            if not response:
                raise RuntimeError("AI返回空结果")
            
            # 解析拆分结果
            split_sentences = []
            for line in response.split('\n'):
                line = line.strip()
                if line and not line.startswith('*') and not line.startswith('-'):
                    # 清理可能的序号
                    line = re.sub(r'^\d+\.\s*', '', line)
                    line = re.sub(r'^[•·]\s*', '', line)
                    if line:
                        split_sentences.append(line)
            
            if not split_sentences:
                raise RuntimeError("AI拆分返回空结果")
            
            return split_sentences
            
        except Exception as e:
            print(f"❌ AI拆分失败: {e}")
            raise