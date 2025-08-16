#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
text_to_audiobook 模块包
提供文本处理和音频书生成相关功能
"""

from .chapter_splitter import ChapterSplitter
from .config import AudiobookConfig

__all__ = ['ChapterSplitter', 'AudiobookConfig']