#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
翻译服务 - 统一的翻译功能
整合字幕翻译和章节标题翻译
"""

import os
import re
import time
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from infra import AIClient, FileManager
from infra.config_loader import AppConfig
from util import parse_srt_file, write_bilingual_srt, BATCH_PROCESSING


class TranslationService:
    """统一的翻译服务"""
    
    def __init__(self, config: AppConfig):
        """
        初始化翻译服务
        
        Args:
            config: 应用配置
        """
        self.config = config
        self.ai_client = AIClient(config.api)
        self.file_manager = FileManager()
    
    def translate_subtitle_files(self, subtitle_files: List[str]) -> List[str]:
        """
        批量翻译字幕文件，使用上下文提升翻译质量
        
        Args:
            subtitle_files: 字幕文件路径列表
            
        Returns:
            成功翻译的文件列表
        """
        if not subtitle_files:
            print("⚠️ 未找到字幕文件，跳过翻译")
            return []
        
        print(f"🌏 开始翻译 {len(subtitle_files)} 个字幕文件...")
        
        translated_files = []
        total_stats = {
            'files_processed': 0,
            'files_failed': 0
        }
        
        for i, subtitle_file in enumerate(subtitle_files, 1):
            try:
                filename = os.path.basename(subtitle_file)
                print(f"🔍 翻译字幕文件 ({i}/{len(subtitle_files)}): {filename}")
                
                if self._translate_single_file(subtitle_file):
                    translated_files.append(subtitle_file)
                    total_stats['files_processed'] += 1
                else:
                    total_stats['files_failed'] += 1
                    total_stats['files_processed'] += 1
                
                # 添加延迟避免API限流
                if i < len(subtitle_files):
                    time.sleep(0.5)
                    
            except Exception as e:
                print(f"❌ 翻译文件时出错 {os.path.basename(subtitle_file)}: {e}")
                total_stats['files_failed'] += 1
                total_stats['files_processed'] += 1
                continue
        
        # 输出最终统计
        print(f"\n📊 翻译完成统计:")
        print(f"   📁 处理文件: {total_stats['files_processed']}")
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
                not entry.get('chinese_text') or 
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
        真正的批量翻译字幕条目（一个API调用处理一批字幕）
        
        Args:
            subtitle_entries: 字幕条目列表
            
        Returns:
            翻译后的字幕条目列表
        """
        translated_entries = subtitle_entries.copy()
        
        # 找出需要翻译的条目
        entries_to_translate = []
        for i, entry in enumerate(subtitle_entries):
            if (not entry.get('chinese_text') or 
                entry['chinese_text'].startswith('[解析失败]') or 
                entry['chinese_text'].startswith('[翻译失败]')):
                entries_to_translate.append((i, entry))
        
        if not entries_to_translate:
            print("✅ 所有字幕已有翻译")
            return translated_entries
        
        print(f"🔄 需要翻译 {len(entries_to_translate)} 条字幕，共 {len(subtitle_entries)} 条")
        
        # 按批量大小分组
        batch_size = BATCH_PROCESSING['translation_batch_size']
        batches = []
        for i in range(0, len(entries_to_translate), batch_size):
            batch = entries_to_translate[i:i + batch_size]
            batches.append(batch)
        
        print(f"🚀 开始批次间并发翻译，共 {len(batches)} 个批次")
        
        # 批次间并发处理
        max_workers = min(len(batches), self.config.api.max_concurrent_workers)  # 限制批次并发数
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有批次任务
            future_to_batch = {}
            for batch_idx, batch in enumerate(batches):
                future = executor.submit(self._translate_single_batch, batch, batch_idx + 1, len(batches))
                future_to_batch[future] = batch
            
            # 收集批次翻译结果
            completed_batches = 0
            for future in as_completed(future_to_batch):
                batch = future_to_batch[future]
                try:
                    batch_results = future.result()
                    if batch_results:
                        # 将批次翻译结果应用到translated_entries
                        self._apply_batch_results(batch_results, batch, translated_entries)
                    completed_batches += 1
                    print(f"    ✅ 批次翻译完成 ({completed_batches}/{len(batches)})")
                except Exception as e:
                    print(f"    ❌ 批次翻译失败: {e}")
                    # 批次失败时标记失败
                    for entry_index, entry in batch:
                        translated_entries[entry_index]['chinese_text'] = f"[翻译失败] {entry['english_text']}"
        
        return translated_entries
    
    def _translate_single_batch(self, batch: List, batch_num: int, total_batches: int) -> Optional[Dict]:
        """
        翻译单个批次（一个API调用处理整批字幕）
        
        Args:
            batch: 需要翻译的条目批次 [(index, entry), ...]
            batch_num: 当前批次号
            total_batches: 总批次数
            
        Returns:
            批次翻译结果字典 {序号: 翻译结果}
        """
        try:
            print(f"    📦 批次 {batch_num}/{total_batches}: 处理 {len(batch)} 条字幕")
            
            # 构建批量翻译prompt
            batch_prompt = self._build_batch_translation_prompt(batch)
            
            # 调用API进行批量翻译
            response = self.ai_client.chat_completion(
                batch_prompt, 
                temperature=0.3, 
                max_tokens=2000
            )
            
            if not response or not response.strip():
                print(f"    ⚠️ 批次 {batch_num} API返回空结果")
                return None
            
            # 解析批量翻译结果
            batch_results = self._parse_batch_translation_result(response, batch)
            return batch_results
            
        except Exception as e:
            print(f"    ❌ 批次 {batch_num} 翻译异常: {e}")
            return None
    
    def _build_batch_translation_prompt(self, batch: List) -> str:
        """
        构建带序号的批量翻译prompt
        
        Args:
            batch: 字幕条目批次 [(index, entry), ...]
            
        Returns:
            批量翻译prompt
        """
        # 构建带序号的英文句子列表
        english_sentences = []
        for i, (entry_index, entry) in enumerate(batch, 1):
            english_sentences.append(f"{i}. {entry['english_text']}")
        
        sentences_text = "\n".join(english_sentences)
        
        prompt = f"""你是专业的英中翻译专家，专门翻译英文字幕。

请翻译以下英文字幕，严格保持序号对应：

{sentences_text}

要求：
1. 准确传达原意，语言自然流畅，表达优美
2. 翻译要求信达雅：准确、流畅、优美
3. 必须保持序号对应，格式为：
   1. 中文翻译1
   2. 中文翻译2
   ...

请开始翻译："""
        
        return prompt
    
    def _parse_batch_translation_result(self, response: str, batch: List) -> Dict[int, str]:
        """
        解析批量翻译结果，按序号配对
        
        Args:
            response: API返回的批量翻译结果
            batch: 原始字幕条目批次
            
        Returns:
            序号到翻译结果的映射 {batch_index: translation}
        """
        results = {}
        lines = response.strip().split('\n')
        
        # 解析每行翻译结果
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # 匹配序号格式：1. 翻译内容
            import re
            match = re.match(r'^(\d+)\.\s*(.+)$', line)
            if match:
                seq_num = int(match.group(1))
                translation = match.group(2).strip()
                
                # 检查序号是否在有效范围内
                if 1 <= seq_num <= len(batch):
                    # 序号从1开始，转换为批次内索引（从0开始）
                    batch_index = seq_num - 1
                    results[batch_index] = translation
        
        return results
    
    def _apply_batch_results(self, batch_results: Dict[int, str], batch: List, translated_entries: List[Dict]):
        """
        将批次翻译结果应用到字幕条目
        
        Args:
            batch_results: 批次翻译结果 {batch_index: translation}
            batch: 原始批次 [(entry_index, entry), ...]
            translated_entries: 目标字幕条目列表
        """
        for batch_idx, (entry_index, entry) in enumerate(batch):
            if batch_idx in batch_results:
                # 有对应翻译结果
                translated_entries[entry_index]['chinese_text'] = batch_results[batch_idx]
            else:
                # 序号不匹配或解析失败
                translated_entries[entry_index]['chinese_text'] = f"[翻译失败] {entry['english_text']}"
    
    def translate_chapter_titles(self, titles: List[str], book_name: str = "") -> List[str]:
        """
        批量翻译章节标题，智能去重相似标题
        
        Args:
            titles: 章节标题列表
            book_name: 书籍名称（用作翻译上下文）
            
        Returns:
            翻译后的标题列表
        """
        if not titles:
            return []
        
        print(f"🌏 开始翻译 {len(titles)} 个章节标题...")
        
        # 分析标题模式，提取唯一模式
        unique_patterns = self._analyze_title_patterns(titles)
        
        # 批量翻译唯一模式
        pattern_translations = self._translate_unique_patterns_batch(unique_patterns, book_name)
        
        # 映射回原标题
        translated_titles = []
        for title in titles:
            pattern = self._extract_title_pattern(title)
            if pattern in pattern_translations:
                # 替换模式为翻译，保留序号
                sequence_match = re.search(r'\d+', title)
                if sequence_match:
                    sequence = sequence_match.group()
                    translated_title = pattern_translations[pattern].replace('{序号}', sequence)
                else:
                    translated_title = pattern_translations[pattern]
                translated_titles.append(translated_title)
            else:
                translated_titles.append(title)  # 翻译失败，保持原标题
        
        print(f"✅ 章节标题翻译完成!")
        return translated_titles
    
    def _analyze_title_patterns(self, titles: List[str]) -> Dict[str, List[str]]:
        """分析标题模式，找出相似的标题"""
        patterns = {}
        
        for title in titles:
            pattern = self._extract_title_pattern(title)
            if pattern not in patterns:
                patterns[pattern] = []
            patterns[pattern].append(title)
        
        return patterns
    
    def _extract_title_pattern(self, title: str) -> str:
        """提取标题模式（将数字替换为占位符）"""
        return re.sub(r'\d+', '{序号}', title)
    
    def _translate_unique_patterns_batch(self, patterns: Dict[str, List[str]], book_name: str) -> Dict[str, str]:
        """批量翻译唯一的标题模式"""
        unique_patterns = list(patterns.keys())
        
        if not unique_patterns:
            return {}
        
        # 构建批量翻译提示词
        context = f"书籍：{book_name}\n" if book_name else ""
        prompt_titles = "\n".join([f"{i+1}. {pattern}" for i, pattern in enumerate(unique_patterns)])
        
        prompt = f"""请翻译以下英文章节标题为中文。注意：
1. 保持标题的格式和风格
2. {{序号}}是占位符，翻译时保持不变
3. 考虑这些标题来自同一本书的不同章节
4. 返回格式：每行一个翻译结果，与输入顺序对应

{context}章节标题：
{prompt_titles}

翻译结果："""
        
        try:
            response = self.ai_client.chat_completion(prompt, temperature=0.1)
            if not response:
                return {}
            
            # 解析翻译结果
            translations = {}
            lines = response.strip().split('\n')
            
            for i, line in enumerate(lines):
                if i >= len(unique_patterns):
                    break
                
                # 清理可能的序号前缀
                line = re.sub(r'^\d+\.\s*', '', line.strip())
                if line:
                    translations[unique_patterns[i]] = line
            
            return translations
            
        except Exception as e:
            print(f"❌ 批量翻译章节标题失败: {e}")
            return {}
    
    def _parse_srt_file(self, subtitle_file: str) -> List[Dict]:
        """解析SRT字幕文件 - 使用统一的解析工具"""
        return parse_srt_file(subtitle_file)
    
    def _write_bilingual_srt(self, entries: List[Dict], subtitle_file: str) -> None:
        """写入双语SRT文件 - 使用统一的写入工具"""
        write_bilingual_srt(entries, subtitle_file)