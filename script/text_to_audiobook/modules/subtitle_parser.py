#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字幕解析模块
使用 SiliconFlow API 对英文字幕进行语言学解析，生成中英文字幕和详细的解析JSON文件
"""

import os
import time
import json
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests


@dataclass
class SubtitleParserConfig:
    """字幕解析配置"""
    
    # API 配置
    api_key: str = ""
    model: str = ""
    timeout: int = 0
    max_retries: int = 0
    max_concurrent_workers: int = 0


    # 请求配置
    base_url: str = "https://api.siliconflow.cn/v1"
    initial_retry_delay: float = 1.0
    max_retry_delay: float = 30.0


class SubtitleParser:
    """字幕解析器 - 生成中英文字幕并创建详细的语言学解析JSON文件"""
    
    def __init__(self, config: SubtitleParserConfig):
        """
        初始化字幕解析器
        
        Args:
            config: 解析配置
        """
        self.config = config
        
        if not self.config.api_key:
            raise RuntimeError("字幕解析器初始化失败: 缺少 SiliconFlow API 密钥")
    
    def parse_subtitle_files(self, subtitle_files: List[str], output_dir: str) -> List[str]:
        """
        批量解析字幕文件，生成中英文字幕和语言学解析JSON文件
        支持格式验证和自动修复功能
        
        Args:
            subtitle_files: 字幕文件路径列表
            output_dir: 输出根目录
            
        Returns:
            成功解析的文件列表
        """        
        parsed_files = []
        total_files = len(subtitle_files)
        
        # 创建解析结果目录
        analysis_dir = os.path.join(output_dir, "parsed_analysis")
        os.makedirs(analysis_dir, exist_ok=True)
        
        print(f"🔄 开始解析 {total_files} 个字幕文件...")
        
        total_stats = {
            'files_processed': 0,
            'files_failed': 0,
            'files_repaired': 0,
            'files_skipped': 0
        }
        
        for i, subtitle_file in enumerate(subtitle_files, 1):
            try:
                filename = os.path.basename(subtitle_file)
                print(f"\n🔍 解析字幕文件 ({i}/{total_files}): {filename}")
                
                # 1. 首先验证字幕文件格式
                validation_result = self._validate_subtitle_format(subtitle_file)
                
                # 2. 如果格式有问题，尝试简单格式修复
                if not validation_result['is_valid']:
                    print(f"⚠️ 字幕格式有问题，类型: {validation_result['error_type']}")
                    
                    # 只对重复中文的问题进行修复
                    if validation_result['error_type'] == 'duplicate_chinese':
                        if self.repair_subtitle_format_only(subtitle_file):
                            total_stats['files_repaired'] += 1
                            print(f"✅ 字幕文件已修复: {filename}")
                        else:
                            print(f"⚠️ 无法修复字幕文件，将重新解析: {filename}")
                    else:
                        print(f"⚠️ 字幕格式问题类型为 {validation_result['error_type']}，将重新解析: {filename}")
                
                # 3. 继续正常的解析流程
                if self._parse_single_file(subtitle_file, analysis_dir):
                    parsed_files.append(subtitle_file)
                    total_stats['files_processed'] += 1
                else:
                    total_stats['files_failed'] += 1
                    total_stats['files_processed'] += 1
                
                # 添加延迟避免API限流
                if i < total_files:
                    time.sleep(0.5)
                    
            except Exception as e:
                print(f"❌ 解析文件时出错 {os.path.basename(subtitle_file)}: {e}")
                total_stats['files_failed'] += 1
                total_stats['files_processed'] += 1
                continue
        
        # 输出最终统计
        print(f"\n📊 解析完成统计:")
        print(f"   📁 处理文件: {total_stats['files_processed']}")
        print(f"   🔧 修复文件: {total_stats['files_repaired']}")
        print(f"   ❌ 失败文件: {total_stats['files_failed']}")
        
        return parsed_files
    
    def translate_subtitle_files(self, subtitle_files: List[str], output_dir: str) -> List[str]:
        """
        批量翻译字幕文件，生成高质量的中英文字幕
        使用上下文翻译提升翻译质量
        
        Args:
            subtitle_files: 字幕文件路径列表
            output_dir: 输出根目录
            
        Returns:
            成功翻译的文件列表
        """
        translated_files = []
        total_files = len(subtitle_files)
        
        print(f"🌏 开始翻译 {total_files} 个字幕文件...")
        
        total_stats = {
            'files_processed': 0,
            'files_failed': 0,
            'files_repaired': 0
        }
        
        for i, subtitle_file in enumerate(subtitle_files, 1):
            try:
                filename = os.path.basename(subtitle_file)
                print(f"\n🔍 翻译字幕文件 ({i}/{total_files}): {filename}")
                
                # 1. 首先验证字幕文件格式
                validation_result = self._validate_subtitle_format(subtitle_file)
                
                # 2. 如果格式有问题，尝试简单格式修复
                if not validation_result['is_valid']:
                    print(f"⚠️ 字幕格式有问题，类型: {validation_result['error_type']}")
                    
                    # 只对重复中文的问题进行修复
                    if validation_result['error_type'] == 'duplicate_chinese':
                        if self.repair_subtitle_format_only(subtitle_file):
                            total_stats['files_repaired'] += 1
                            print(f"✅ 字幕文件已修复: {filename}")
                        else:
                            print(f"⚠️ 无法修复字幕文件，将重新翻译: {filename}")
                    else:
                        print(f"⚠️ 字幕格式问题类型为 {validation_result['error_type']}，将重新翻译: {filename}")
                
                # 3. 继续正常的翻译流程
                if self._translate_single_file(subtitle_file):
                    translated_files.append(subtitle_file)
                    total_stats['files_processed'] += 1
                else:
                    total_stats['files_failed'] += 1
                    total_stats['files_processed'] += 1
                
                # 添加延迟避免API限流
                if i < total_files:
                    time.sleep(0.5)
                    
            except Exception as e:
                print(f"❌ 翻译文件时出错 {os.path.basename(subtitle_file)}: {e}")
                total_stats['files_failed'] += 1
                total_stats['files_processed'] += 1
                continue
        
        # 输出最终统计
        print(f"\n📊 翻译完成统计:")
        print(f"   📁 处理文件: {total_stats['files_processed']}")
        print(f"   🔧 修复文件: {total_stats['files_repaired']}")
        print(f"   ❌ 失败文件: {total_stats['files_failed']}")
        
        return translated_files
    
    def _translate_single_file(self, subtitle_file: str) -> bool:
        """
        翻译单个字幕文件，使用上下文提升翻译质量
        
        Args:
            subtitle_file: 字幕文件路径
            
        Returns:
            是否翻译成功
        """
        try:
            # 解析SRT文件
            subtitle_entries = self._parse_srt_file(subtitle_file)
            if not subtitle_entries:
                print(f"⚠️ 文件无有效字幕: {os.path.basename(subtitle_file)}")
                return False
            
            # 检查是否需要翻译
            needs_translation = any(
                not entry['chinese_text'] or 
                entry['chinese_text'].startswith('[解析失败]') or 
                entry['chinese_text'].startswith('[翻译失败]')
                for entry in subtitle_entries
            )
            
            if not needs_translation:
                print(f"✅ 字幕已完整翻译，跳过: {os.path.basename(subtitle_file)}")
                return True
            
            print(f"🌏 开始上下文翻译，共 {len(subtitle_entries)} 条字幕")
            
            # 批量翻译字幕条目
            translated_entries = self._translate_subtitle_entries_with_context(subtitle_entries)
            if not translated_entries:
                return False
            
            # 写回原文件
            self._write_bilingual_srt(translated_entries, subtitle_file)
            
            return True
            
        except Exception as e:
            print(f"❌ 翻译单个文件失败: {e}")
            return False
    
    def _translate_subtitle_entries_with_context(self, subtitle_entries: List[Dict]) -> List[Dict]:
        """
        使用上下文批量翻译字幕条目
        
        Args:
            subtitle_entries: 字幕条目列表
            
        Returns:
            翻译后的字幕条目列表
        """
        translated_entries = subtitle_entries.copy()
        total_entries = len(subtitle_entries)
        
        # 找出需要翻译的条目
        entries_to_translate = []
        for i, entry in enumerate(subtitle_entries):
            if (not entry['chinese_text'] or 
                entry['chinese_text'].startswith('[解析失败]') or 
                entry['chinese_text'].startswith('[翻译失败]')):
                entries_to_translate.append((i, entry))
        
        if not entries_to_translate:
            print("✅ 所有字幕已有翻译")
            return translated_entries
        
        print(f"🔄 需要翻译 {len(entries_to_translate)} 条字幕，共 {total_entries} 条")
        
        # 分批处理（按并发数分批）
        batch_size = self.config.max_concurrent_workers
        for i in range(0, len(entries_to_translate), batch_size):
            batch = entries_to_translate[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(entries_to_translate) + batch_size - 1) // batch_size
            
            print(f"  翻译批次 {batch_num}/{total_batches} ({len(batch)} 条字幕)")
            
            # 翻译当前批次
            self._translate_batch_with_context(batch, subtitle_entries, translated_entries)
            
            # 添加延迟避免API限流
            if i + batch_size < len(entries_to_translate):
                time.sleep(0.5)
        
        return translated_entries
    
    def _translate_batch_with_context(self, batch: List[Tuple[int, Dict]], all_entries: List[Dict], result_entries: List[Dict]):
        """
        使用上下文翻译一批字幕条目（并发版本）
        
        Args:
            batch: 需要翻译的条目批次 [(index, entry), ...]
            all_entries: 所有字幕条目（用于获取上下文）
            result_entries: 结果条目列表（会被修改）
        """
        print(f"    🚀 开始并发上下文翻译 {len(batch)} 条字幕...")
        
        # 使用线程池进行并发处理
        max_workers = min(len(batch), self.config.max_concurrent_workers)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_info = {}
            for entry_index, entry in batch:
                # 获取上下文
                context = self._get_context_for_translation(entry_index, all_entries)
                future = executor.submit(self._translate_with_context, entry['english_text'], context, int(entry['index']))
                future_to_info[future] = (entry_index, entry)
            
            completed_count = 0
            for future in as_completed(future_to_info):
                entry_index, entry = future_to_info[future]
                try:
                    translation = future.result()
                    if translation:
                        result_entries[entry_index]['chinese_text'] = translation
                    else:
                        result_entries[entry_index]['chinese_text'] = f"[翻译失败] {entry['english_text']}"
                    
                    completed_count += 1
                    print(f"    ✅ 翻译完成字幕 {entry['index']} ({completed_count}/{len(batch)})")
                    
                except Exception as e:
                    print(f"    ❌ 翻译字幕 {entry['index']} 失败: {e}")
                    result_entries[entry_index]['chinese_text'] = f"[翻译失败] {entry['english_text']}"
    
    def _get_context_for_translation(self, entry_index: int, all_entries: List[Dict]) -> Dict[str, Optional[str]]:
        """
        获取翻译所需的上下文信息
        
        Args:
            entry_index: 当前条目在列表中的索引
            all_entries: 所有字幕条目列表
            
        Returns:
            上下文字典，包含previous、current、next
        """
        context = {
            'previous': None,
            'current': all_entries[entry_index]['english_text'],
            'next': None
        }
        
        # 获取前一句
        if entry_index > 0:
            context['previous'] = all_entries[entry_index - 1]['english_text']
        
        # 获取后一句
        if entry_index < len(all_entries) - 1:
            context['next'] = all_entries[entry_index + 1]['english_text']
        
        return context
    
    def _translate_with_context(self, current_text: str, context: Dict[str, Optional[str]], subtitle_index: int) -> Optional[str]:
        """
        使用上下文翻译单个句子
        
        Args:
            current_text: 当前需要翻译的句子
            context: 上下文信息
            subtitle_index: 字幕索引（用于日志）
            
        Returns:
            翻译结果或None（表示失败）
        """
        try:
            print(f"    📝 带上下文翻译字幕 {subtitle_index}: {current_text}")
            
            # 构建上下文翻译提示词
            system_prompt = """你是专业的英中翻译专家，专门翻译英文字幕。

要求：
1. 根据提供的上下文理解句子的语境和情感
2. 只翻译标记为"当前句子"的内容  
3. 翻译要求信达雅：准确传达原意，语言自然流畅，表达优美
4. 考虑上下文的连贯性，但只输出当前句的翻译
5. 只返回翻译结果，无需其他内容"""
            
            # 构建用户提示词
            context_parts = []
            if context['previous']:
                context_parts.append(f"前一句: {context['previous']}")
            
            context_parts.append(f"当前句子: {current_text}")
            
            if context['next']:
                context_parts.append(f"后一句: {context['next']}")
            
            user_prompt = "\\n".join(context_parts)
            user_prompt += "\\n\\n请翻译当前句子:"
            
            # 调用API
            response = self._call_unified_api(system_prompt, user_prompt, max_tokens=500, temperature=0.3)
            if response and response.strip():
                return response.strip()
            else:
                print(f"    ⚠️ 字幕 {subtitle_index} API返回空结果")
                return None
                
        except Exception as e:
            print(f"    ❌ 翻译字幕 {subtitle_index} 异常: {e}")
            return None
    
    def _parse_single_file(self, subtitle_file: str, analysis_dir: str) -> bool:
        """
        解析单个字幕文件，专注于语言学分析（语法、词汇、短语等）
        支持增量解析：只重新处理失败的字幕行
        
        Args:
            subtitle_file: 字幕文件路径
            analysis_dir: 解析结果输出目录
            
        Returns:
            是否解析成功
        """
        try:
            # 解析SRT文件
            subtitle_entries = self._parse_srt_file(subtitle_file)
            if not subtitle_entries:
                print(f"⚠️ 文件无有效字幕: {os.path.basename(subtitle_file)}")
                return False
            
            # 检查现有解析结果
            subtitle_name = os.path.splitext(os.path.basename(subtitle_file))[0]
            json_file = os.path.join(analysis_dir, f"{subtitle_name}.json")
            
            # 获取需要重新处理的字幕索引（包括失败和未处理的）
            total_subtitles = len(subtitle_entries)
            unprocessed_indices = self._get_unprocessed_subtitle_indices(json_file, total_subtitles)
            
            if not unprocessed_indices:
                print(f"✅ 所有字幕已成功解析，跳过文件: {os.path.basename(subtitle_file)}")
                return True
            
            # 过滤出需要重新解析的字幕条目
            entries_to_parse = [entry for entry in subtitle_entries 
                              if int(entry['index']) in unprocessed_indices]
            print(f"🔄 发现 {len(unprocessed_indices)} 条需要处理的字幕，共 {total_subtitles} 条")
            print(f"📝 需要重新解析的字幕索引: {sorted(list(unprocessed_indices))}")
            
            if not entries_to_parse:
                print(f"✅ 无需重新解析任何字幕")
                return True
            
            # 批量解析需要处理的字幕条目
            newly_parsed_entries = self._parse_subtitle_entries(entries_to_parse)
            if not newly_parsed_entries:
                return False
            
            # 如果是增量解析，需要合并结果
            if unprocessed_indices and os.path.exists(json_file):
                # 读取现有的所有结果
                existing_results = self._load_existing_analysis(json_file)
                
                # 将新解析的结果转换为JSON格式
                new_analysis_results = []
                for entry in newly_parsed_entries:
                    analysis_json = {
                        "subtitle_index": int(entry['index']),
                        "english_text": entry['english_text']
                    }
                    
                    if 'analysis' in entry and entry['analysis']:
                        analysis_json.update(entry['analysis'])
                    else:
                        # 如果没有分析结果，设置默认值
                        analysis_json.update({
                            "sentence_structure": "",
                            "key_words": [],
                            "fixed_phrases": [],
                            "core_grammar": [],
                            "colloquial_expression": []
                        })
                    
                    new_analysis_results.append(analysis_json)
                
                # 合并现有结果与新结果
                merged_results = self._merge_analysis_results(existing_results, new_analysis_results)
                
                # 语言学解析不处理翻译，保持原有的中文文本
                # 翻译需要使用单独的 translate_subtitle_files 方法
                
                # 使用合并后的结果
                final_parsed_entries = subtitle_entries
                
                # 直接写入合并后的JSON结果
                self._write_merged_analysis_json(merged_results, json_file)
            else:
                # 首次解析，直接使用新结果
                final_parsed_entries = newly_parsed_entries
                # 写入JSON解析结果
                self._write_analysis_json(final_parsed_entries, subtitle_file, analysis_dir)
            
            # 写回原文件，包含中英文
            self._write_bilingual_srt(final_parsed_entries, subtitle_file)
            
            return True
            
        except Exception as e:
            print(f"❌ 解析单个文件失败: {e}")
            return False
    
    def _parse_srt_file(self, srt_path: str) -> List[Dict]:
        """解析SRT文件"""
        subtitle_entries = []
        
        try:
            with open(srt_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # 按空行分割字幕条目
            blocks = content.split('\n\n')
            
            for block in blocks:
                lines = block.strip().split('\n')
                if len(lines) >= 3:
                    # 解析字幕条目
                    index = lines[0].strip()
                    timestamp = lines[1].strip()
                    text = '\n'.join(lines[2:]).strip()
                    
                    subtitle_entries.append({
                        'index': index,
                        'timestamp': timestamp,
                        'english_text': text,
                        'chinese_text': ''
                    })
            
            return subtitle_entries
            
        except Exception as e:
            print(f"解析SRT文件失败: {e}")
            return []
    
    def _parse_subtitle_entries(self, subtitle_entries: List[Dict]) -> List[Dict]:
        """批量解析字幕条目"""
        parsed_entries = []
        total_entries = len(subtitle_entries)
        
        # 分批处理（按并发数分批）
        batch_size = self.config.max_concurrent_workers
        for i in range(0, total_entries, batch_size):
            batch = subtitle_entries[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total_entries + batch_size - 1) // batch_size
            
            print(f"  解析批次 {batch_num}/{total_batches} ({len(batch)} 条字幕)")
            
            # 解析当前批次
            parsed_batch = self._parse_batch(batch)
            if parsed_batch:
                parsed_entries.extend(parsed_batch)
            else:
                # 解析失败，保留原英文
                for entry in batch:
                    entry['chinese_text'] = f"[解析失败] {entry['english_text']}"
                    entry['analysis'] = {}
                parsed_entries.extend(batch)
            
            # 添加延迟避免API限流
            if i + batch_size < total_entries:
                time.sleep(0.5)
        
        return parsed_entries
    
    def _get_unprocessed_subtitle_indices(self, json_file_path: str, total_subtitle_count: int) -> set:
        """
        读取现有JSON文件，返回需要重新处理的字幕索引集合（包括失败和未处理的）
        
        Args:
            json_file_path: JSON解析结果文件路径
            total_subtitle_count: SRT文件中的总字幕数
            
        Returns:
            包含需要重新处理的字幕索引的集合
        """
        unprocessed_indices = set()
        processed_indices = set()
        
        if not os.path.exists(json_file_path):
            # 如果文件不存在，所有字幕都需要处理
            return set(range(1, total_subtitle_count + 1))
            
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
            # 按行分割，每行是一个JSON对象
            for line_num, line in enumerate(content.split('\n'), 1):
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    analysis_data = json.loads(line)
                    translation = analysis_data.get('translation', '')
                    subtitle_index = analysis_data.get('subtitle_index', line_num)
                    
                    # 记录已处理的索引
                    processed_indices.add(subtitle_index)
                    
                    # 检查是否包含失败标识
                    if translation.startswith('[解析失败]'):
                        unprocessed_indices.add(subtitle_index)
                        
                except json.JSONDecodeError as e:
                    print(f"⚠️ 跳过无效JSON行 {line_num}: {e}")
                    continue
                    
        except Exception as e:
            print(f"⚠️ 读取现有解析文件失败 {json_file_path}: {e}")
            # 出错时返回所有索引
            return set(range(1, total_subtitle_count + 1))
        
        # 找出未处理的字幕索引
        all_indices = set(range(1, total_subtitle_count + 1))
        missing_indices = all_indices - processed_indices
        
        # 合并失败和未处理的索引
        unprocessed_indices.update(missing_indices)
        
        return unprocessed_indices
    
    def _merge_analysis_results(self, existing_results: List[Dict], new_results: List[Dict]) -> List[Dict]:
        """
        合并现有解析结果与新解析结果
        
        Args:
            existing_results: 现有的解析结果列表
            new_results: 新的解析结果列表
            
        Returns:
            合并后的解析结果列表
        """
        # 创建现有结果的索引映射
        existing_map = {result.get('subtitle_index', 0): result for result in existing_results}
        
        # 创建新结果的索引映射
        new_map = {result.get('subtitle_index', 0): result for result in new_results}
        
        # 合并结果：新结果优先，未更新的保持原结果
        merged_results = []
        all_indices = set(existing_map.keys()) | set(new_map.keys())
        
        for index in sorted(all_indices):
            if index in new_map:
                merged_results.append(new_map[index])
            elif index in existing_map:
                merged_results.append(existing_map[index])
                
        return merged_results
    
    def _load_existing_analysis(self, json_file_path: str) -> List[Dict]:
        """
        加载现有的解析结果JSON文件
        
        Args:
            json_file_path: JSON文件路径
            
        Returns:
            解析结果列表
        """
        existing_results = []
        
        if not os.path.exists(json_file_path):
            return existing_results
            
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
            # 按行分割，每行是一个JSON对象
            for line_num, line in enumerate(content.split('\n'), 1):
                line = line.strip()
                if not line:
                    continue
                    
                try:
                    analysis_data = json.loads(line)
                    existing_results.append(analysis_data)
                except json.JSONDecodeError as e:
                    print(f"⚠️ 跳过无效JSON行 {line_num}: {e}")
                    continue
                    
        except Exception as e:
            print(f"⚠️ 加载现有解析结果失败 {json_file_path}: {e}")
            
        return existing_results
    
    def _write_merged_analysis_json(self, merged_results: List[Dict], json_file_path: str):
        """
        写入合并后的解析结果到JSON文件
        
        Args:
            merged_results: 合并后的解析结果列表
            json_file_path: JSON文件路径
        """
        try:
            with open(json_file_path, 'w', encoding='utf-8') as f:
                for result in merged_results:
                    json_line = json.dumps(result, ensure_ascii=False)
                    f.write(json_line + '\n')
                    
            print(f"✅ 合并解析结果已写入: {os.path.basename(json_file_path)}")
            
        except Exception as e:
            print(f"❌ 写入合并解析结果失败: {e}")
    
    def _parse_batch(self, batch: List[Dict]) -> Optional[List[Dict]]:
        """解析一批字幕条目（并发版本）"""
        print(f"    🚀 开始并发解析 {len(batch)} 条字幕...")
        
        # 使用线程池进行并发处理
        max_workers = min(len(batch), self.config.max_concurrent_workers)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_entry = {
                executor.submit(self._analyze_single_sentence_safe, entry): entry 
                for entry in batch
            }
            
            parsed_batch = []
            completed_count = 0
            for future in as_completed(future_to_entry):
                entry = future_to_entry[future]
                try:
                    analysis_result = future.result()
                    if analysis_result:
                        # 语言学解析成功，但不包含翻译
                        entry['analysis'] = analysis_result
                        # 翻译字段标记为需要单独处理
                        if not entry.get('chinese_text'):
                            entry['chinese_text'] = f"[需要翻译] {entry['english_text']}"
                    else:
                        entry['analysis'] = {}
                        entry['chinese_text'] = f"[解析失败] {entry['english_text']}"
                    
                    parsed_batch.append(entry)
                    completed_count += 1
                    print(f"    ✅ 语言学分析完成字幕 {entry['index']} ({completed_count}/{len(batch)})")
                    
                except Exception as e:
                    print(f"    ❌ 解析字幕 {entry['index']} 失败: {e}")
                    entry['analysis'] = {}
                    entry['chinese_text'] = f"[解析失败] {entry['english_text']}"
                    parsed_batch.append(entry)
        
        # 按原始顺序排序
        parsed_batch.sort(key=lambda x: int(x['index']))
        return parsed_batch
    
    def _analyze_single_sentence_safe(self, entry: Dict) -> Optional[Dict]:
        """
        线程安全的单个句子分析方法
        
        Args:
            entry: 字幕条目字典
            
        Returns:
            解析结果或None
        """
        try:
            english_text = entry['english_text']
            print(f"    📝 解析字幕 {entry['index']}: {english_text}")
            
            # 调用现有的分析方法
            return self._analyze_single_sentence(english_text)
            
        except Exception as e:
            print(f"    ❌ 线程解析失败: {e}")
            return None
    
    def _analyze_single_sentence(self, english_text: str) -> Optional[Dict]:
        """
        分析单个英文句子的语言学特征，专注于语法、词汇、短语分析
        不包含翻译功能，翻译由单独的方法处理
        
        Args:
            english_text: 英文句子
            
        Returns:
            包含语言学分析的字典，或None表示失败
        """
        # 构建纯语言学分析提示词
        system_prompt = """IMPORTANT: 只返回JSON格式，不要任何额外文字或解释。

作为英语语言学家，请分析用户输入的英语句子，并严格按以下JSON格式输出语言学分析。

字段要求:
- sentence_structure: 句法成分分析（主语+谓语+宾语+状语等）
- key_words: 句子中有意义的词汇，排除the、a、is、Mrs.等常见词
- fixed_phrases: 有固定含义的短语搭配，排除过于简单的组合
- core_grammar: 重要语法现象（时态、语态、句式等）
- colloquial_expression: 正式与口语表达对比

输出格式:
{
  "sentence_structure": "句子结构分析",
  "key_words": [{"word": "单词", "pos": "词性", "meaning": "含义", "pronunciation": "音标"}],
  "fixed_phrases": [{"phrase": "短语", "meaning": "含义"}],
  "core_grammar": [{"point": "语法点", "explanation": "解释"}],
  "colloquial_expression": [{"formal": "正式表达", "informal": "口语表达", "explanation": "用法说明"}]
}

示例1 (复合句):
输入: "The project that we've been working on for months, which involves multiple stakeholders, will be completed once we receive the final approval."
输出:
{
  "sentence_structure": "主语(The project) + 定语从句1(that we've been working on for months) + 定语从句2(which involves multiple stakeholders) + 谓语(will be completed) + 时间状语从句(once we receive the final approval)",
  "key_words": [{"word": "stakeholders", "pos": "n.", "meaning": "利益相关者", "pronunciation": "/ˈsteɪkhoʊldərz/"}, {"word": "approval", "pos": "n.", "meaning": "批准，同意", "pronunciation": "/əˈpruːvəl/"}],
  "fixed_phrases": [{"phrase": "work on", "meaning": "从事，致力于"}],
  "core_grammar": [{"point": "定语从句嵌套", "explanation": "两个定语从句修饰同一主语，'that'引导限制性定语从句，'which'引导非限制性定语从句"}],
  "colloquial_expression": [{"formal": "receive the final approval", "informal": "get the green light", "explanation": "'get the green light'表示获得许可，比'receive approval'更生动"}]
}

示例2 (简单句):
输入: "She is very happy."
输出:
{
  "sentence_structure": "主语(She) + 系动词(is) + 表语(very happy)",
  "key_words": [],
  "fixed_phrases": [],
  "core_grammar": [],
  "colloquial_expression": []
}

注意: 无相关内容时字段留空(空数组[]或空字符串"")，但不可省略字段。记住：仅输出JSON格式。"""

        user_prompt = f"请分析以下英语句子: \"{english_text}\""
        
        try:
            # 调用统一的API进行分析
            response = self._call_unified_api(system_prompt, user_prompt, max_tokens=1500, temperature=0.2)
            if not response:
                return None
            
            # 解析JSON响应
            return self._parse_analysis_response(response)
            
        except Exception as e:
            print(f"    ❌ 句子分析API调用失败: {e}")
            return None
    
    def _call_unified_api(self, system_prompt: str, user_prompt: str, max_tokens: int = 1500, temperature: float = 0.2) -> Optional[str]:
        """统一的API调用方法，支持不同类型的请求"""
        url = f"{self.config.base_url}/chat/completions"
        
        headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "authorization": f"Bearer {self.config.api_key}"
        }
        
        payload = {
            "model": self.config.model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user", 
                    "content": user_prompt
                }
            ],
            "stream": False,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        # 带指数退避的重试机制
        retry_delay = self.config.initial_retry_delay
        
        for attempt in range(self.config.max_retries + 1):
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=self.config.timeout)
                response.raise_for_status()
                
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content']
                    if attempt > 0:
                        print(f"✅ API调用在第{attempt + 1}次尝试后成功")
                    return content.strip()
                else:
                    raise RuntimeError(f"API响应格式异常: {result}")
                    
            except Exception as e:
                if attempt == self.config.max_retries:
                    print(f"❌ API调用失败，已达到最大重试次数({self.config.max_retries + 1}次)")
                    print(f"最后错误: {e}")
                    return None
                
                print(f"⚠️ API调用失败(第{attempt + 1}次尝试): {e}")
                print(f"将在{retry_delay}秒后重试...")
                time.sleep(retry_delay)
                
                # 指数退避，但不超过最大延迟
                retry_delay = min(retry_delay * 2, self.config.max_retry_delay)
        
        return None
    
    def _parse_analysis_response(self, response: str) -> Optional[Dict]:
        """解析API返回的语言学分析结果（不包含翻译）"""
        try:
            # 尝试直接解析JSON
            analysis = json.loads(response)
            
            # 验证必要字段（移除translation字段）
            required_fields = ['sentence_structure', 'key_words', 'fixed_phrases', 'core_grammar', 'colloquial_expression']
            for field in required_fields:
                if field not in analysis:
                    analysis[field] = [] if field != 'sentence_structure' else ""
            
            return analysis
            
        except json.JSONDecodeError as e:
            print(f"    ❌ JSON解析失败: {e}")
            # 尝试提取可能的JSON片段
            try:
                # 查找JSON开始和结束标记
                start_idx = response.find('{')
                end_idx = response.rfind('}')
                if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                    json_text = response[start_idx:end_idx+1]
                    analysis = json.loads(json_text)
                    
                    # 验证字段（移除translation字段）
                    required_fields = ['sentence_structure', 'key_words', 'fixed_phrases', 'core_grammar', 'colloquial_expression']
                    for field in required_fields:
                        if field not in analysis:
                            analysis[field] = [] if field != 'sentence_structure' else ""
                    
                    return analysis
            except:
                pass
            
            return None
        except Exception as e:
            print(f"    ❌ 解析响应失败: {e}")
            return None
    
    def _write_analysis_json(self, parsed_entries: List[Dict], subtitle_file: str, analysis_dir: str):
        """将解析结果写入JSON文件"""
        try:
            # 获取字幕文件名（不包含扩展名）
            subtitle_name = os.path.splitext(os.path.basename(subtitle_file))[0]
            json_file = os.path.join(analysis_dir, f"{subtitle_name}.json")
            
            with open(json_file, 'w', encoding='utf-8') as f:
                for entry in parsed_entries:
                    # 构建输出JSON对象
                    output_json = {
                        "subtitle_index": int(entry['index']),
                        "english_text": entry['english_text']
                    }
                    
                    # 添加语言学分析结果（不包含翻译）
                    if 'analysis' in entry and entry['analysis']:
                        output_json.update(entry['analysis'])
                    else:
                        # 如果没有分析结果，设置默认值
                        output_json.update({
                            "sentence_structure": "",
                            "key_words": [],
                            "fixed_phrases": [],
                            "core_grammar": [],
                            "colloquial_expression": []
                        })
                    
                    # 写入一行JSON
                    f.write(json.dumps(output_json, ensure_ascii=False, separators=(',', ':')) + '\n')
            
            print(f"    ✅ 解析结果已保存到: {json_file}")
            
        except Exception as e:
            print(f"    ❌ 保存解析结果失败: {e}")
    
    
    def _validate_subtitle_format(self, subtitle_file: str) -> Dict[str, any]:
        """
        验证字幕文件格式是否符合规范（索引、时间戳、英文、中文翻译）
        
        Args:
            subtitle_file: 字幕文件路径
            
        Returns:
            验证结果字典，包含is_valid、error_type、error_details等
        """
        result = {
            'is_valid': False,
            'error_type': None,
            'error_details': [],
            'total_blocks': 0,
            'corrupted_blocks': []
        }
        
        try:
            with open(subtitle_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                result['error_type'] = 'empty_file'
                result['error_details'].append("字幕文件为空")
                print(f"⚠️ 字幕文件为空: {os.path.basename(subtitle_file)}")
                return result
            
            # 按空行分割字幕条目
            blocks = content.split('\n\n')
            result['total_blocks'] = len(blocks)
            expected_index = 1
            has_format_errors = False
            has_duplicate_chinese = False
            
            for i, block in enumerate(blocks):
                lines = block.strip().split('\n')
                
                # 每个字幕条目应该有4行：索引、时间戳、英文、中文
                if len(lines) != 4:
                    has_format_errors = True
                    corrupted_info = {
                        'block_index': i + 1,
                        'expected_lines': 4,
                        'actual_lines': len(lines),
                        'lines_content': lines
                    }
                    result['corrupted_blocks'].append(corrupted_info)
                    
                    # 检查是否是重复中文的情况
                    if len(lines) == 5:
                        # 检查第4和第5行是否相同（重复中文）
                        if len(lines) >= 5 and lines[3].strip() == lines[4].strip():
                            has_duplicate_chinese = True
                            corrupted_info['duplicate_chinese'] = True
                    
                    print(f"⚠️ 字幕条目 {i+1} 格式错误：应该有4行，实际有{len(lines)}行")
                    continue
                
                # 验证索引
                try:
                    index = int(lines[0].strip())
                    if index != expected_index:
                        has_format_errors = True
                        result['corrupted_blocks'].append({
                            'block_index': i + 1,
                            'error': 'index_mismatch',
                            'expected': expected_index,
                            'actual': index
                        })
                        print(f"⚠️ 字幕索引不连续，期望{expected_index}，实际{index}")
                    expected_index = index + 1
                except ValueError:
                    has_format_errors = True
                    result['corrupted_blocks'].append({
                        'block_index': i + 1,
                        'error': 'invalid_index',
                        'content': lines[0]
                    })
                    print(f"⚠️ 字幕索引格式错误: {lines[0]}")
                    expected_index += 1
                
                # 验证时间戳格式（仅在有4行时验证）
                if len(lines) >= 4:
                    timestamp = lines[1].strip()
                    if ' --> ' not in timestamp:
                        has_format_errors = True
                        result['corrupted_blocks'].append({
                            'block_index': i + 1,
                            'error': 'invalid_timestamp',
                            'content': timestamp
                        })
                        print(f"⚠️ 时间戳格式错误: {timestamp}")
                    
                    # 验证英文和中文不为空
                    english_text = lines[2].strip()
                    chinese_text = lines[3].strip()
                    
                    if not english_text:
                        has_format_errors = True
                        result['corrupted_blocks'].append({
                            'block_index': i + 1,
                            'error': 'empty_english'
                        })
                        print(f"⚠️ 字幕条目 {expected_index-1} 英文为空")
                    
                    if not chinese_text:
                        has_format_errors = True
                        result['corrupted_blocks'].append({
                            'block_index': i + 1,
                            'error': 'empty_chinese'
                        })
                        print(f"⚠️ 字幕条目 {expected_index-1} 中文翻译为空")
                    
                    # 检查中文翻译是否包含失败标识
                    if chinese_text.startswith('[解析失败]') or chinese_text.startswith('[翻译失败]'):
                        has_format_errors = True
                        result['corrupted_blocks'].append({
                            'block_index': i + 1,
                            'error': 'translation_failed',
                            'content': chinese_text[:30]
                        })
                        print(f"⚠️ 字幕条目 {expected_index-1} 包含翻译失败标识: {chinese_text[:20]}...")
            
            # 设置错误类型
            if has_duplicate_chinese:
                result['error_type'] = 'duplicate_chinese'
            elif has_format_errors:
                result['error_type'] = 'format_error'
            else:
                result['is_valid'] = True
                print(f"✅ 字幕文件格式验证通过: {os.path.basename(subtitle_file)}")
            
            return result
            
        except Exception as e:
            result['error_type'] = 'read_error'
            result['error_details'].append(str(e))
            print(f"❌ 字幕文件格式验证失败 {os.path.basename(subtitle_file)}: {e}")
            return result
    
    def repair_subtitle_format_only(self, subtitle_file: str) -> bool:
        """
        仅修复SRT字幕文件的格式问题（行数超过4行的情况）
        不依赖JSON文件，只处理明显的格式错误
        
        Args:
            subtitle_file: 需要修复的字幕文件路径
            
        Returns:
            是否修复成功
        """
        try:
            print(f"🔧 开始修复字幕格式: {os.path.basename(subtitle_file)}")
            
            # 读取原文件
            with open(subtitle_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                print(f"⚠️ 字幕文件为空，无需修复")
                return True
            
            # 备份原文件
            backup_file = f"{subtitle_file}.backup"
            try:
                import shutil
                shutil.copy2(subtitle_file, backup_file)
                print(f"📋 已备份原文件到: {backup_file}")
            except Exception as e:
                print(f"⚠️ 备份文件失败: {e}")
            
            # 按空行分割字幕条目
            blocks = content.split('\n\n')
            fixed_blocks = []
            repaired_count = 0
            skipped_count = 0
            
            for i, block in enumerate(blocks):
                lines = block.strip().split('\n')
                
                # 格式正确的条目直接保留
                if len(lines) == 4:
                    fixed_blocks.append(block)
                    continue
                
                # 行数超过4的条目进行修复
                elif len(lines) > 4:
                    # 检查前4行是否完整：索引、时间戳、英文、中文
                    if len(lines) >= 4:
                        try:
                            # 验证索引是否为数字
                            int(lines[0].strip())
                            
                            # 验证时间戳格式
                            timestamp = lines[1].strip()
                            if ' --> ' not in timestamp:
                                skipped_count += 1
                                continue
                            
                            # 检查英文和中文是否都有内容
                            english_text = lines[2].strip()
                            chinese_text = lines[3].strip()
                            
                            if not english_text:
                                skipped_count += 1
                                continue
                            
                            # 如果中文为空或是解析失败标记，跳过此条目
                            if not chinese_text or chinese_text.startswith('[解析失败]') or chinese_text.startswith('[翻译失败]'):
                                skipped_count += 1
                                continue
                            
                            # 只保留前4行，修复格式
                            fixed_block = '\n'.join(lines[:4])
                            fixed_blocks.append(fixed_block)
                            repaired_count += 1
                            
                        except ValueError:
                            # 索引不是数字，跳过
                            skipped_count += 1
                            continue
                    else:
                        # 行数不够4行，跳过
                        skipped_count += 1
                        continue
                
                # 行数少于4的条目跳过
                else:
                    skipped_count += 1
                    continue
            
            # 如果没有修复任何条目，删除备份文件并返回成功
            if repaired_count == 0:
                try:
                    os.remove(backup_file)
                except:
                    pass
                print(f"✅ 没有发现需要修复的格式问题")
                return True
            
            # 重写文件
            with open(subtitle_file, 'w', encoding='utf-8') as f:
                for i, block in enumerate(fixed_blocks):
                    f.write(block)
                    if i < len(fixed_blocks) - 1:  # 最后一个条目后不加空行
                        f.write('\n\n')
            
            # 简化验证：只检查每个条目是否有4行，不检查索引连续性
            print(f"✅ 字幕格式修复完成: 修复了{repaired_count}个条目，跳过了{skipped_count}个条目")
            
            # 删除备份文件
            try:
                os.remove(backup_file)
            except:
                pass
            return True
                
        except Exception as e:
            print(f"❌ 字幕格式修复失败: {e}")
            # 尝试恢复备份文件
            try:
                import shutil
                shutil.move(f"{subtitle_file}.backup", subtitle_file)
            except:
                pass
            return False
    
    def _extract_original_srt_structure(self, subtitle_file: str) -> List[Dict]:
        """
        提取原SRT文件的结构信息（索引和时间戳）
        智能处理损坏的SRT文件格式
        
        Args:
            subtitle_file: 字幕文件路径
            
        Returns:
            结构信息列表
        """
        try:
            with open(subtitle_file, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            if not content:
                return []
            
            structure = []
            blocks = content.split('\n\n')
            
            for i, block in enumerate(blocks):
                lines = block.strip().split('\n')
                if len(lines) >= 2:  # 至少要有索引和时间戳
                    try:
                        index = int(lines[0].strip())
                        timestamp = lines[1].strip()
                        
                        # 提取英文（第3行总是英文）
                        english_text = ""
                        if len(lines) >= 3:
                            english_text = lines[2].strip()
                        
                        structure.append({
                            'index': index,
                            'timestamp': timestamp,
                            'english_text': english_text
                        })
                    except ValueError:
                        # 索引不是数字，跳过这个条目
                        print(f"⚠️ 跳过无效索引的条目: {lines[0] if lines else 'empty'}")
                        continue
                        
            print(f"📝 从SRT文件提取了 {len(structure)} 个有效条目")
            return structure
            
        except Exception as e:
            print(f"❌ 提取SRT结构失败: {e}")
            return []
    
    def _rebuild_srt_from_json(self, srt_structure: List[Dict], json_data: List[Dict], output_file: str) -> bool:
        """
        从SRT结构和JSON数据重建SRT文件
        
        Args:
            srt_structure: 原SRT的结构信息
            json_data: JSON解析数据
            output_file: 输出文件路径
            
        Returns:
            是否重建成功
        """
        try:
            # 创建JSON数据的索引映射
            json_map = {item.get('subtitle_index', 0): item for item in json_data}
            
            with open(output_file, 'w', encoding='utf-8') as f:
                for struct in srt_structure:
                    index = struct['index']
                    timestamp = struct['timestamp']
                    
                    # 从JSON数据获取中文翻译，英文优先使用原SRT结构中的
                    json_item = json_map.get(index)
                    
                    # 优先使用原SRT结构中的英文，避免JSON中可能的重复内容
                    english_text = struct.get('english_text', '')
                    
                    if json_item and json_item.get('translation'):
                        chinese_text = json_item.get('translation', '')
                        
                        # 如果JSON中的英文为空或者包含失败标记，则使用结构中的英文
                        json_english = json_item.get('english_text', '')
                        if not english_text and json_english and not json_english.startswith('[解析失败]'):
                            # 清理JSON中可能存在的重复内容
                            if '\\n[解析失败]' in json_english:
                                english_text = json_english.split('\\n[解析失败]')[0].strip()
                            elif '\\n' in json_english:
                                # 取第一行作为英文
                                english_text = json_english.split('\\n')[0].strip()
                            else:
                                english_text = json_english
                    else:
                        # 如果JSON中没有对应数据或翻译为空，中文标记为需要解析
                        chinese_text = f"[解析失败] {english_text}"
                    
                    # 写入标准的4行格式
                    f.write(f"{index}\n")
                    f.write(f"{timestamp}\n")
                    f.write(f"{english_text}\n")
                    f.write(f"{chinese_text}\n\n")
            
            print(f"✅ 重建SRT文件成功，共写入 {len(srt_structure)} 个条目")
            return True
            
        except Exception as e:
            print(f"❌ 重建SRT文件失败: {e}")
            return False
    
    def _write_bilingual_srt(self, translated_entries: List[Dict], output_path: str):
        """写入中英文双语SRT文件，直接覆盖原文件"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for entry in translated_entries:
                f.write(f"{entry['index']}\n")
                f.write(f"{entry['timestamp']}\n")
                f.write(f"{entry['english_text']}\n")
                f.write(f"{entry['chinese_text']}\n\n")
    

    def test_connection(self) -> bool:
        """测试API连接"""
        print("正在测试 SiliconFlow API 连接...")
        try:
            response = self._call_unified_api("你是一个AI助手", "请回答：你好", max_tokens=50, temperature=0.3)
            if response:
                print(f"✅ API连接成功，响应: {response[:50]}...")
                return True
            else:
                print("❌ API连接失败")
                return False
        except Exception as e:
            print(f"❌ API连接测试失败: {e}")
            return False