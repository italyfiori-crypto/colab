#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
时间工具函数
"""


def format_duration(seconds: float) -> str:
    """
    格式化时长为可读格式
    
    Args:
        seconds: 秒数
        
    Returns:
        格式化的时长字符串
    """
    if seconds < 60:
        return f"{seconds:.1f}秒"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}分钟"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}小时"


def calculate_percentage(part: float, total: float) -> float:
    """
    计算百分比
    
    Args:
        part: 部分值
        total: 总值
        
    Returns:
        百分比
    """
    if total == 0:
        return 0.0
    return (part / total) * 100