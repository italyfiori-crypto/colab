#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
句子拆分与翻译模块
使用AI同时进行句子拆分和翻译，确保语义一致性
"""

import os
import re
import json
import time
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from infra import AIClient, FileManager
from infra.config_loader import AppConfig


class SentenceProcessor:
    """句子拆分与翻译处理器"""
    
    def __init__(self, config: AppConfig):
        """
        初始化句子处理器
        
        Args:
            config: 应用配置
        """
        self.config = config
        self.ai_client = AIClient(config.api)
        self.file_manager = FileManager()
    
    def split_sub_chapters_to_sentences(self, input_files: List[str], output_dir: str) -> List[str]:
        """
        拆分文件列表为句子级文件（JSONL格式）
        
        Args:
            input_files: 输入文件路径列表
            output_dir: 输出目录
            
        Returns:
            生成的句子文件路径列表
        """
        # 创建输出目录
        sentences_dir = os.path.join(output_dir, "sentences")
        os.makedirs(sentences_dir, exist_ok=True)
        
        output_files = []
        
        print(f"🔍 开始AI拆分翻译 {len(input_files)} 个子章节文件...")
        
        for i, input_file in enumerate(input_files, 1):
            try:
                # 生成输出文件路径
                filename = os.path.basename(input_file)
                base_name = os.path.splitext(filename)[0]
                output_file = os.path.join(sentences_dir, f"{base_name}.jsonl")
                
                print(f"📄 [{i}/{len(input_files)}] 处理文件: {filename}")
                
                # 处理单个文件
                success = self._process_file(input_file, output_file)
                if success:
                    output_files.append(output_file)
                    print(f"    ✅ 已完成AI拆分翻译: {filename}")
                else:
                    print(f"    ❌ 处理失败: {filename}")
                    
            except Exception as e:
                print(f"    ❌ 拆分翻译失败: {e}")
                continue
        
        print(f"\n📁 句子拆分翻译完成，输出到: {sentences_dir}")
        print(f"📊 成功处理: {len(output_files)}/{len(input_files)} 个文件")
        
        return output_files
    
    def _process_file(self, input_file: str, output_file: str) -> bool:
        """
        处理单个文件的句子拆分和翻译（增量处理）
        
        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径
            
        Returns:
            是否处理成功
        """
        try:
            # 读取输入文件
            with open(input_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取标题和正文
            title, body = self._extract_title_and_body(content)
            
            if not body.strip():
                print(f"    ⚠️ 文件内容为空，跳过")
                return False
            
            # 按段落分割
            paragraphs = re.split(r'\n\n', body)
            paragraphs = [p.strip() for p in paragraphs if p.strip()]
            
            print(f"    🔍 处理 {len(paragraphs)} 个段落")
            
            # 加载已有处理结果
            existing_results = self._load_existing_paragraph_results(output_file)
            processed_indices = {result['paragraph_index'] for result in existing_results if result.get('success', False)}
            
            # 识别未处理的段落
            unprocessed_paragraphs = []
            for para_idx, paragraph in enumerate(paragraphs, 1):
                if para_idx not in processed_indices:
                    unprocessed_paragraphs.append((para_idx, paragraph))
            
            if not unprocessed_paragraphs:
                print(f"    ✅ 所有段落已处理完毕，跳过")
                return True
            
            print(f"    🔄 需要处理 {len(unprocessed_paragraphs)}/{len(paragraphs)} 个段落")
            
            # 并发处理未完成的段落
            new_results = []
            max_workers = min(len(unprocessed_paragraphs), self.config.api.max_concurrent_workers)
            
            print(f"    🚀 开始并发处理，使用 {max_workers} 个worker")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有段落任务
                future_to_paragraph = {}
                for para_idx, paragraph in unprocessed_paragraphs:
                    future = executor.submit(self._process_single_paragraph, para_idx, paragraph, len(paragraphs))
                    future_to_paragraph[future] = (para_idx, paragraph)
                
                # 收集并发处理结果
                completed_count = 0
                for future in as_completed(future_to_paragraph):
                    para_idx, paragraph = future_to_paragraph[future]
                    try:
                        paragraph_result = future.result()
                        if paragraph_result:
                            new_results.append(paragraph_result)
                        else:
                            # 创建失败结果
                            paragraph_result = {
                                "paragraph_index": para_idx,
                                "original_text": paragraph,
                                "segments": [],
                                "success": False
                            }
                            new_results.append(paragraph_result)
                        
                        completed_count += 1
                        if completed_count % 3 == 0 or completed_count == len(unprocessed_paragraphs):
                            print(f"    📊 并发进度: {completed_count}/{len(unprocessed_paragraphs)} 个段落")
                            
                    except Exception as e:
                        print(f"    ❌ 段落 {para_idx} 并发处理异常: {e}")
                        # 记录失败的段落
                        paragraph_result = {
                            "paragraph_index": para_idx,
                            "original_text": paragraph,
                            "segments": [],
                            "success": False
                        }
                        new_results.append(paragraph_result)
            
            # 保存结果（追加模式）
            if new_results:
                self._save_paragraph_results(output_file, new_results, existing_results)
                
                success_count = sum(1 for result in new_results if result['success'])
                print(f"    💾 已保存 {len(new_results)} 个段落结果，成功 {success_count} 个")
                return success_count > 0
            else:
                print(f"    ⚠️ 未生成新的段落结果")
                return False
                
        except Exception as e:
            print(f"    ❌ 文件处理异常: {e}")
            return False
    
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
    
    def _process_single_paragraph(self, para_idx: int, paragraph: str, total_paragraphs: int) -> Optional[Dict]:
        """
        处理单个段落（用于并发）
        
        Args:
            para_idx: 段落索引
            paragraph: 段落内容
            total_paragraphs: 总段落数
            
        Returns:
            段落处理结果，失败返回None
        """
        try:
            print(f"      📝 段落 {para_idx}/{total_paragraphs}: {len(paragraph)} 字符")
            
            # 使用AI进行拆分和翻译
            segments = self._split_and_translate_with_ai(paragraph)
            
            # 构建段落结果
            paragraph_result = {
                "paragraph_index": para_idx,
                "original_text": paragraph,
                "segments": segments if segments else [],
                "success": bool(segments)
            }
            
            if segments:
                print(f"      ✅ 段落 {para_idx} 生成 {len(segments)} 个句子片段")
            else:
                print(f"      ❌ 段落 {para_idx} 处理失败")
            
            return paragraph_result
            
        except Exception as e:
            print(f"      ❌ 段落 {para_idx} 处理异常: {e}")
            return None
    
    def _split_and_translate_with_ai(self, paragraph: str) -> List[Dict[str, str]]:
        """
        使用AI同时进行句子拆分和翻译
        
        Args:
            paragraph: 输入段落
            
        Returns:
            拆分翻译结果列表 [{"original": "英文", "translation": "中文"}, ...]
        """
        try:
            system_prompt = """作为英语句子拆分与翻译专家，请将英文段落按语义完整性拆分并翻译成中文。

## 输出格式
每行一个句子对，格式：英文 || 中文
不要任何其他说明或格式标记。

## 拆分规则
1. **长度控制**：
   - 短句（≤15个单词）：保持完整，不拆分
   - 长句（>15个单词）：拆分为8-15个单词的片段
   - 严禁超过15个单词的片段

2. **拆分原则**：
   - 在自然停顿处拆分（从句边界、连词、标点）
   - 保持语义完整性和逻辑连贯性
   - 不破坏习语和固定搭配
   - 严格保留原文所有内容（标点、大小写、斜体等）

## 翻译要求
- **信达雅**：准确传意，中文流畅，保持文学性
- 恰当处理斜体强调和对话引语
- 自然处理括号补充说明

## 示例
输入：Alice was beginning to get very tired of sitting by her sister on the bank, and of having nothing to do.

输出：
Alice was beginning to get very tired of sitting by her sister on the bank, || 爱丽丝开始对坐在姐姐身边的河岸上感到非常疲倦，
and of having nothing to do. || 也厌倦了无所事事。"""
            
            user_prompt = f"请对以下英文段落进行拆分和翻译：\n\n{paragraph}"
            
            # 调用AI API
            response = self.ai_client.chat_completion(
                user_prompt, 
                system_prompt,
                temperature=0.8, 
                max_tokens=4000
            )
            
            if not response or not response.strip():
                print(f"      ⚠️ AI返回空结果")
                return []
            
            # 解析句子对响应
            try:
                # 使用新的句子对解析方法
                sentences = self._parse_sentence_pairs(response)
                
                if sentences:
                    return sentences
                else:
                    print(f"      ⚠️ 未解析到有效的句子对")
                    return []
                    
            except Exception as e:
                print(f"      ⚠️ 句子对解析失败: {e}")
                return []
                
        except Exception as e:
            print(f"      ❌ AI拆分翻译异常: {e}")
            return []
    
    def _parse_sentence_pairs(self, response: str) -> List[Dict[str, str]]:
        """
        从AI响应中解析双竖线分隔的句子对
        
        Args:
            response: AI返回的原始响应
            
        Returns:
            解析的句子对列表 [{"original": "英文", "translation": "中文"}, ...]
        """
        if not response:
            return []
        
        sentences = []
        try:
            # 按行分割响应
            lines = response.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                # 跳过空行
                if not line:
                    continue
                
                # 检查是否包含双竖线分隔符
                if '||' in line:
                    # 只分割第一个||，防止翻译文本中的||被误分割
                    parts = line.split('||', 1)
                    if len(parts) == 2:
                        original = parts[0].strip()
                        translation = parts[1].strip()
                        
                        # 验证内容不为空
                        if original and translation:
                            sentences.append({
                                'original': original,
                                'translation': translation
                            })
            
            return sentences
            
        except Exception as e:
            print(f"      ⚠️ 解析句子对失败: {e}")
            return []
    
    def _load_existing_paragraph_results(self, output_file: str) -> List[Dict]:
        """
        加载已有的段落处理结果
        
        Args:
            output_file: 输出文件路径
            
        Returns:
            已有的段落结果列表
        """
        if not os.path.exists(output_file):
            return []
        
        results = []
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        result = json.loads(line)
                        if isinstance(result, dict) and 'paragraph_index' in result:
                            results.append(result)
                    except json.JSONDecodeError as e:
                        print(f"      ⚠️ 解析JSON行 {line_num} 失败: {e}")
                        continue
                        
        except Exception as e:
            print(f"      ⚠️ 读取已有结果文件失败 {output_file}: {e}")
            
        return results
    
    def _save_paragraph_results(self, output_file: str, new_results: List[Dict], existing_results: List[Dict]):
        """
        保存段落处理结果（合并新旧结果）
        
        Args:
            output_file: 输出文件路径
            new_results: 新的处理结果
            existing_results: 已有的处理结果
        """
        try:
            # 合并结果：用新结果覆盖相同段落索引的旧结果
            all_results = {}
            
            # 先添加已有结果
            for result in existing_results:
                para_idx = result.get('paragraph_index')
                if para_idx is not None:
                    all_results[para_idx] = result
            
            # 再添加新结果（覆盖相同索引）
            for result in new_results:
                para_idx = result.get('paragraph_index')
                if para_idx is not None:
                    all_results[para_idx] = result
            
            # 按段落索引排序并写入文件
            sorted_results = sorted(all_results.values(), key=lambda x: x.get('paragraph_index', 0))
            
            with open(output_file, 'w', encoding='utf-8') as f:
                for result in sorted_results:
                    f.write(json.dumps(result, ensure_ascii=False) + '\n')
                    
        except Exception as e:
            print(f"      ❌ 保存段落结果失败: {e}")
            raise