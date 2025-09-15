#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SRT字幕文件解析工具 - 统一的解析逻辑
提供标准的SRT文件解析功能，供各个服务使用
"""

from typing import List, Dict
from infra import FileManager


def parse_srt_file(subtitle_file: str) -> List[Dict]:
    """
    解析SRT字幕文件
    
    Args:
        subtitle_file: 字幕文件路径
        
    Returns:
        字幕条目列表，每个条目包含：
        - index: 序号
        - timestamp: 时间戳
        - english_text: 英文字幕
        - chinese_text: 中文字幕（如果有）
    """
    try:
        file_manager = FileManager()
        content = file_manager.read_text_file(subtitle_file)
        entries = []
        
        # 按空行分割字幕条目
        blocks = [block.strip() for block in content.split('\n\n') if block.strip()]
        
        for block in blocks:
            lines = block.split('\n')
            if len(lines) >= 3:
                entry = {
                    'index': lines[0].strip(),
                    'timestamp': lines[1].strip(),
                    'english_text': lines[2].strip(),
                    'chinese_text': lines[3].strip() if len(lines) > 3 else ''
                }
                entries.append(entry)
        
        return entries
        
    except Exception as e:
        print(f"❌ 解析SRT文件失败 {subtitle_file}: {e}")
        return []


def write_bilingual_srt(entries: List[Dict], subtitle_file: str) -> None:
    """
    写入双语SRT文件
    
    Args:
        entries: 字幕条目列表
        subtitle_file: 输出文件路径
    """
    try:
        file_manager = FileManager()
        content_lines = []
        
        for entry in entries:
            content_lines.append(entry['index'])
            content_lines.append(entry['timestamp'])
            content_lines.append(entry['english_text'])
            content_lines.append(entry['chinese_text'])
            content_lines.append('')  # 空行分隔
        
        content = '\n'.join(content_lines)
        file_manager.write_text_file(subtitle_file, content)
        
    except Exception as e:
        print(f"❌ 写入SRT文件失败 {subtitle_file}: {e}")
        raise