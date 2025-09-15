# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个文本转有声书工具，可以将书籍文本拆分为章节、子章节和句子，并生成音频和字幕。该工具支持英语语音合成、字幕语言学解析（包含翻译、语法分析、词汇解释等）、词汇提取与分级等功能。

## 核心架构

项目采用三层架构设计：

### 基础设施层 (`infra/`)
- **ai_client.py** - 统一的AI API客户端，处理所有AI服务调用
- **file_manager.py** - 文件操作管理器，提供统一的文件读写接口
- **config_loader.py** - 配置加载器，支持多种配置格式

### 业务逻辑层 (`service/`)
- **text_processor.py** - 文本处理服务，整合章节、子章节、句子拆分
- **audio_processor.py** - 音频处理服务，整合音频生成和压缩
- **translation_service.py** - 翻译服务，处理字幕翻译和章节标题翻译
- **analysis_service.py** - 分析服务，进行语言学分析和统计收集
- **vocabulary_service.py** - 词汇服务，处理词汇提取和分级
- **workflow_executor.py** - 工作流执行器，协调所有处理步骤

### 工具函数层 (`util/`)
- **file_utils.py** - 文件操作工具函数
- **time_utils.py** - 时间格式化工具函数
- **directory_constants.py** - 硬编码的目录结构和常量

### 流程设计

该工具采用模块化流程设计，主要处理步骤：

1. 文本处理（章节拆分 → 子章节拆分 → 句子拆分）→ 2. 音频生成 → 3. 翻译和分析 → 4. 词汇处理

所有输出目录结构固定，无需配置。

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
- `api.api_key` - API密钥
- `text_processing.ai_split_threshold` - AI拆分阈值

所有目录结构、base_url等已硬编码，无需配置。

## 关键技术依赖

- **DeepSeek API** - AI服务，用于句子拆分、翻译、语言学分析
- **Python requests** - HTTP客户端，用于API调用
- **JSON** - 配置和数据交换格式

## 输出目录结构

```
output/<book_name>/
├── chapters/         # 章节文件
├── sub_chapters/     # 子章节文件  
├── sentences/        # 句子文件
├── audio/           # 音频文件（暂未实现）
├── subtitles/       # 中英文字幕文件
├── parsed_analysis/ # 字幕语言学解析JSON文件
├── compressed_audio/ # 压缩音频（暂未实现）
├── vocabulary/      # 词汇文件（暂未实现）
└── meta.json        # 统计信息
```

注：目录结构已硬编码在代码中，无需配置。

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