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
        
        prompt = f"""请翻译以下英文章节标题为中文。**必须严格保持行数一一对应**：

{context}章节标题：
{prompt_titles}

翻译要求：
1. **行数对应：输出行数必须与输入行数完全相等
2. **顺序对应：第N行输出对应第N行输入**
3. **格式保持：{{序号}}是占位符，翻译时必须保持不变**
4. 保持标题的格式和风格
5. 考虑这些标题来自同一本书的不同章节

格式示例：
输入：
1. The Beginning  
2. The Journey
3. The End

输出：
开始
旅程  
结束

**重要：**
- 每行对应一个标题翻译
- 不要添加序号前缀（如"1."）
- 不要添加任何额外解释或说明

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