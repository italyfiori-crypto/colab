#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JSONL字幕文件解析工具 - 统一的解析逻辑
提供标准的JSONL字幕文件解析功能，供各个服务使用
"""

import json
from typing import List, Dict
from infra import FileManager


def parse_jsonl_subtitle_file(subtitle_file: str) -> List[Dict]:
    """
    解析JSONL字幕文件
    
    Args:
        subtitle_file: 字幕文件路径
        
    Returns:
        字幕条目列表，每个条目包含：
        - index: 序号
        - timestamp: 时间戳
        - english_text: 英文字幕
        - chinese_text: 中文字幕
        - has_analysis: 是否有分析结果（可选）
    """
    try:
        file_manager = FileManager()
        content = file_manager.read_text_file(subtitle_file)
        entries = []
        
        # 按行解析JSONL格式
        for line_num, line in enumerate(content.split('\n'), 1):
            line = line.strip()
            if not line:
                continue
            
            try:
                entry = json.loads(line)
                # 验证必需字段
                if isinstance(entry, dict) and 'index' in entry and 'timestamp' in entry:
                    entries.append(entry)
                else:
                    print(f"⚠️ 字幕条目格式错误，行 {line_num}")
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON解析失败，行 {line_num}: {e}")
                continue
        
        return entries
        
    except Exception as e:
        print(f"❌ 解析JSONL字幕文件失败 {subtitle_file}: {e}")
        return []


def write_jsonl_subtitle_file(entries: List[Dict], subtitle_file: str) -> None:
    """
    写入JSONL字幕文件
    
    Args:
        entries: 字幕条目列表
        subtitle_file: 输出文件路径
    """
    try:
        file_manager = FileManager()
        lines = []
        
        for entry in entries:
            line = json.dumps(entry, ensure_ascii=False, separators=(',', ':'))
            lines.append(line)
        
        content = '\n'.join(lines)
        file_manager.write_text_file(subtitle_file, content)
        
    except Exception as e:
        print(f"❌ 写入JSONL字幕文件失败 {subtitle_file}: {e}")
        raise