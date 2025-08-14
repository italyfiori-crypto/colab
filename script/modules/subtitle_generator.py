#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字幕生成模块
生成SRT格式字幕文件，支持时间轴计算和基本的引号修复
"""

from pathlib import Path
from datetime import timedelta
from typing import List, Dict


class SubtitleGenerator:
    """字幕生成器"""
    
    def __init__(self):
        """初始化字幕生成器"""
        pass
    
    def generate_subtitle(self, text: str, duration: float, output_path: Path, 
                         text_splitter, chapter_offset: float = 0) -> int:
        """
        生成SRT字幕文件
        
        Args:
            text: 文本内容
            duration: 音频时长
            output_path: 输出字幕文件路径
            text_splitter: 文本分割器实例
            chapter_offset: 章节时间偏移（用于合并字幕）
            
        Returns:
            字幕条目数量
        """
        print(f"正在生成字幕: {output_path.name}")
        
        # 使用文本分割器生成短字幕条目
        segments = text_splitter.split_text(text, max_length=120)
        
        if not segments:
            return 0
        
        # 计算字幕时间轴
        subtitle_entries = self._calculate_subtitle_timing(segments, duration, chapter_offset)
        
        # 简单的引号修复
        subtitle_entries = self._fix_basic_quotes(subtitle_entries)
        
        # 写入SRT文件
        self._write_srt_file(subtitle_entries, output_path)
        
        subtitle_count = len(subtitle_entries)
        print(f"字幕生成完成，共 {subtitle_count} 条字幕")
        return subtitle_count
    
    def _calculate_subtitle_timing(self, segments: List[str], total_duration: float, 
                                  chapter_offset: float = 0) -> List[Dict]:
        """
        计算字幕时间轴
        
        Args:
            segments: 文本段落列表
            total_duration: 总音频时长
            chapter_offset: 章节时间偏移
            
        Returns:
            字幕条目列表
        """
        subtitle_entries = []
        
        # 计算每段的权重（基于单词数和标点符号）
        segment_weights = []
        for segment in segments:
            words = len(segment.split())
            # 标点符号影响语音停顿
            punctuation_weight = (segment.count(',') * 0.3 + 
                                segment.count(';') * 0.5 + 
                                segment.count(':') * 0.4 + 
                                segment.count('.') * 0.8)
            
            # 引语需要更多时间
            quote_weight = segment.count('"') * 0.2
            
            # 复合权重
            weight = words + punctuation_weight + quote_weight
            segment_weights.append(weight)
        
        total_weight = sum(segment_weights)
        current_time = chapter_offset
        
        for i, (segment, weight) in enumerate(zip(segments, segment_weights)):
            segment = segment.strip()
            if not segment:
                continue
            
            # 基于权重分配时间
            base_duration = (weight / total_weight) * total_duration
            
            # 设置最小和最大显示时间
            min_duration = max(2.0, len(segment) / 80)  # 最少2秒
            max_duration = min(8.0, len(segment) / 15)  # 最多8秒
            
            # 应用时间限制
            segment_duration = max(min_duration, min(max_duration, base_duration))
            
            start_time = current_time
            end_time = current_time + segment_duration
            
            # 格式化时间戳
            start_timestamp = self._format_timestamp(start_time)
            end_timestamp = self._format_timestamp(end_time)
            
            subtitle_entries.append({
                'index': len(subtitle_entries) + 1,
                'start': start_timestamp,
                'end': end_timestamp,
                'text': segment
            })
            
            current_time = end_time
        
        return subtitle_entries
    
    def _fix_basic_quotes(self, subtitle_entries: List[Dict]) -> List[Dict]:
        """
        基本的引号修复
        
        Args:
            subtitle_entries: 原始字幕条目列表
            
        Returns:
            修复后的字幕条目列表
        """
        if not subtitle_entries:
            return subtitle_entries
        
        fixed_entries = []
        
        for i, entry in enumerate(subtitle_entries):
            text = entry['text']
            fixed_text = text
            
            # 简单规则：如果当前条目以 '" ' 开头，且上一条包含未配对的引号
            if text.startswith('" ') and i > 0 and len(fixed_entries) > 0:
                prev_text = fixed_entries[-1]['text']
                
                # 检查上一条是否有未配对的引号
                prev_quotes = prev_text.count('"')
                if prev_quotes % 2 == 1:  # 奇数个引号
                    # 移除当前条目的开头引号
                    fixed_text = text[2:]  # 去掉 '" '
                    
                    # 在上一条末尾添加结束引号
                    if prev_text.endswith('.'):
                        fixed_entries[-1]['text'] = prev_text[:-1] + '."'
                    elif prev_text.endswith(('?', '!')):
                        fixed_entries[-1]['text'] = prev_text + '"'
                    else:
                        fixed_entries[-1]['text'] = prev_text + '"'
            
            # 创建修复后的条目
            fixed_entry = entry.copy()
            fixed_entry['text'] = fixed_text
            fixed_entries.append(fixed_entry)
        
        return fixed_entries
    
    def _format_timestamp(self, seconds: float) -> str:
        """格式化时间戳为SRT格式"""
        td = timedelta(seconds=seconds)
        hours = int(td.total_seconds() // 3600)
        minutes = int((td.total_seconds() % 3600) // 60)
        seconds = td.total_seconds() % 60
        milliseconds = int((seconds % 1) * 1000)
        seconds = int(seconds)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"
    
    def _write_srt_file(self, subtitle_entries: List[Dict], output_path: Path):
        """写入SRT文件"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for entry in subtitle_entries:
                f.write(f"{entry['index']}\n")
                f.write(f"{entry['start']} --> {entry['end']}\n")
                f.write(f"{entry['text']}\n\n")