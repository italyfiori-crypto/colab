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
            system_prompt = """⚠️ 严格要求：必须且只能返回JSON数组格式！

# 句子拆分与翻译专家

## ❌ 绝对禁止返回的内容
- 任何文字说明、解释、注释
- 代码块标记（如```json```）
- 前言、总结、提示性文字
- 除JSON数组外的任何其他格式

## ✅ 正确输出格式示例

### 示例1：短句保持完整（不拆分）
输入：Alice was beginning to get very tired.
输出：
[
  {"original": "Alice was beginning to get very tired.", "translation": "爱丽丝开始感到非常疲倦。"}
]

### 示例2：长句合理拆分
输入：Alice was beginning to get very tired of sitting by her sister on the bank, and of having nothing to do.
输出：
[
  {"original": "Alice was beginning to get very tired of sitting by her sister on the bank,", "translation": "爱丽丝开始对坐在姐姐身边的河岸上感到非常疲倦，"},
  {"original": "and of having nothing to do.", "translation": "也厌倦了无所事事。"}
]

### 示例3：超长句必须充分拆分
输入：Alice had learnt several things of this sort in her lessons in the schoolroom, and though this was not a very good opportunity for showing off her knowledge, as there was no one to listen to her, still it was good practice.
输出：
[
  {"original": "Alice had learnt several things of this sort in her lessons in the schoolroom,", "translation": "爱丽丝在学校里上课时学过很多这类东西，"},
  {"original": "and though this was not a very good opportunity for showing off her knowledge,", "translation": "虽然这不是炫耀她知识的好机会，"},
  {"original": "as there was no one to listen to her,", "translation": "因为没有人听她说话，"},
  {"original": "still it was good practice.", "translation": "但这仍然是很好的练习。"}
]

## 任务描述
请将给定的英文长句按照**语义完整性**拆分成合适的片段，然后对每个片段进行信达雅的中文翻译。

## 核心原则
**严格保持原文完整性**：不得以任何方式修改、重组、删减或添加原文内容，包括所有标点符号、大小写、斜体等格式标记。

## 拆分规则
1. **长度控制**：
   - 短句（≤15个单词）：保持原样，不拆分
   - 长句（>15个单词）：必须拆分为8-15个单词的片段
   - 严禁生成超过15个单词的片段
2. **拆分判断**：
   - 优先考虑句子是否已经足够简洁完整
   - 避免不必要的过度拆分短句
   - 确保长句充分拆分，不留过长片段
3. **拆分原则**：
   - 保持语义完整性，在自然停顿处拆分
   - 严格遵循原文的语法结构和标点符号进行拆分
   - 优先在从句边界、连词、标点处拆分
   - 保持修辞结构和逻辑连贯性
   - 避免破坏习语和固定搭配
   - 长句必须充分拆分，确保每个片段都在合理长度范围内
3. **格式保留**：
   - 完整保留所有标点符号（逗号、分号、引号、括号等）
   - 保留斜体标记 `_word_` 不作任何改动
   - 保留对话的直接引语形式
   - 保持括号内容的完整性

## 翻译要求
- **信**：准确传达原意，不遗漏任何细节
- **达**：中文流畅自然，符合中文表达习惯
- **雅**：文学性表达，保持原文风格韵味
   - 恰当处理斜体强调（在翻译中使用中文强调表达）
   - 保持对话的直接引语形式
   - 自然处理括号内的补充说明

## 输出格式要求
- 必须是有效的JSON数组
- 数组中每个对象必须包含"original"和"translation"两个字段
- 不允许有任何额外的文字或格式

## 🔥 最终强调：
- 只返回纯JSON数组！绝不允许任何其他内容！
- 短句（≤15词）保持完整，避免过度拆分！
- 长句（>15词）必须充分拆分为8-15词片段！
- 严禁生成超过15个单词的片段！
- 每个片段必须在合理长度范围内（8-15词）！"""
            
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
            
            # 解析JSON响应
            try:
                # 智能提取JSON内容
                json_str = self._extract_json_from_response(response)
                if not json_str:
                    print(f"      ⚠️ 无法从响应中提取JSON")
                    return []
                
                sentences = json.loads(json_str)
                
                # 验证结果格式
                if not isinstance(sentences, list):
                    print(f"      ⚠️ JSON格式错误，不是数组")
                    return []
                
                valid_sentences = []
                for sentence in sentences:
                    if isinstance(sentence, dict) and 'original' in sentence and 'translation' in sentence:
                        valid_sentences.append({
                            'original': sentence['original'].strip(),
                            'translation': sentence['translation'].strip()
                        })
                
                if valid_sentences:
                    return valid_sentences
                else:
                    print(f"      ⚠️ 未找到有效的句子对象")
                    return []
                    
            except json.JSONDecodeError as e:
                print(f"      ⚠️ JSON解析失败: {e}")
                return []
                
        except Exception as e:
            print(f"      ❌ AI拆分翻译异常: {e}")
            return []
    
    def _extract_json_from_response(self, response: str) -> str:
        """
        从AI响应中智能提取JSON内容
        
        Args:
            response: AI返回的原始响应
            
        Returns:
            提取的JSON字符串，失败返回空字符串
        """
        if not response:
            return ""
        
        # 清理响应内容
        response = response.strip()
        
        # 1. 尝试移除代码块标记
        if response.startswith('```json'):
            response = response[7:]  # 移除 ```json
        if response.startswith('```'):
            response = response[3:]  # 移除 ```
        if response.endswith('```'):
            response = response[:-3]  # 移除结尾的 ```
        
        response = response.strip()
        
        # 2. 寻找第一个[和最后一个]
        first_bracket = response.find('[')
        last_bracket = response.rfind(']')
        
        if first_bracket != -1 and last_bracket != -1 and last_bracket > first_bracket:
            json_str = response[first_bracket:last_bracket + 1]
            return json_str
        
        # 3. 如果已经是完整JSON格式，直接返回
        if response.startswith('[') and response.endswith(']'):
            return response
        
        return ""
    
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