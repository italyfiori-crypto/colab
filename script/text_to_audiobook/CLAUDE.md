# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个文本转有声书工具，可以将书籍文本拆分为章节、子章节和句子，并生成音频和字幕。该工具支持英语语音合成、字幕语言学解析（包含翻译、语法分析、词汇解释等）、词汇提取与分级等功能。

## 核心架构

### 主要模块 (`modules/`)

- **workflow_executor.py** - 核心流程执行器，协调所有处理步骤
- **chapter_splitter.py** - 章节拆分，基于正则表达式模式识别章节
- **sub_chapter_splitter.py** - 子章节拆分，按阅读时长自动分段
- **sentence_splitter.py** - 句子拆分，支持pySBD和NLTK两种分割器
- **audio_generator.py** - 音频生成，使用Kokoro TTS引擎
- **subtitle_parser.py** - 字幕解析，使用DeepSeek API进行语言学分析
- **vocabulary_manager.py** - 词汇管理，提取和富化单词信息
- **audio_compressor.py** - 音频压缩，转换为MP3格式
- **statistics_collector.py** - 统计信息收集
- **config.py** - 统一配置管理

### 流程设计

该工具采用模块化流程设计，每个步骤相对独立：

1. 章节拆分 → 2. 子章节拆分 → 3. 句子拆分 → 4. 音频生成 → 5. 字幕解析 → 6. 音频压缩 → 7. 词汇处理 → 8. 统计收集

每个步骤都有相应的配置选项和独立的输出目录。

## 开发命令

### 环境依赖安装
```bash
# 必需的Python库
pip3 install nltk pysbd spacy torch soundfile

# 下载spaCy英文模型  
python3 -m spacy download en_core_web_sm

# 下载NLTK数据包
python3 -c "import nltk; nltk.download('punkt')"
```

### 运行程序
```bash
# 基本用法：只拆分文本
python3 main.py data/book.txt --split

# 完整流程：拆分+音频生成+解析+词汇处理
python3 main.py data/book.txt --split --audio --parse --vocabulary

# 添加压缩和统计
python3 main.py data/book.txt --split --audio --parse --compress --stats --verbose
```

### 配置文件

主配置文件：`config.json`

关键配置项：
- `chapter_patterns` - 章节识别正则表达式模式
- `sub_chapter.max_reading_minutes` - 子章节最大阅读时长
- `sentence.segmenter` - 句子分割器选择 (pysbd/nltk)
- `subtitle_parser.api_key` - 解析API密钥
- `audio_compression.format` - 音频压缩格式设置

## 关键技术依赖

- **Kokoro TTS** - 语音合成引擎，需要torch和相关模型文件
- **pySBD** - 推荐的句子边界检测库，对引号对话处理更好
- **NLTK** - 备用句子分割器
- **spaCy** - 用于短句拆分功能
- **DeepSeek API** - 字幕语言学解析服务
- **FFmpeg** - 音频压缩 (通过soundfile调用)

## 输出目录结构

```
output/<book_name>/
├── chapters/         # 章节文件
├── sub_chapters/     # 子章节文件  
├── sentences/        # 句子文件
├── audio/           # 音频文件
├── subtitles/       # 中英文字幕文件
├── parsed_analysis/ # 字幕语言学解析JSON文件
├── compressed_audio/ # 压缩音频
├── vocabulary/      # 词汇文件
└── meta.json        # 统计信息
```

## 错误处理和调试

- 使用 `--verbose` 参数获取详细日志
- 程序会显示各步骤的耗时统计
- 配置文件错误会在启动时检测
- 支持单独执行各个处理步骤，无需完整重跑

## 配置模式说明

### 章节识别模式
项目支持多种书籍格式的章节识别：
- `alice_style` - 爱丽丝梦游仙境格式
- `numeric_style` - 数字章节格式  
- `prince` - 小王子格式
- `ys` - 自定义格式

每种模式使用不同的多行正则表达式匹配章节标题和内容。