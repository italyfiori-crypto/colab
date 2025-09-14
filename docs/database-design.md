# 英语学习小程序数据库设计文档

## 目录

- [1. 数据库架构概述](#1-数据库架构概述)
  - [1.1 设计原则](#11-设计原则)
  - [1.2 技术架构](#12-技术架构)
- [2. 核心数据表设计](#2-核心数据表设计)
  - [2.1 用户信息表 (users)](#21-用户信息表-users)
  - [2.2 书籍信息表 (books)](#22-书籍信息表-books)
  - [2.3 章节内容表 (chapters)](#23-章节内容表-chapters)
  - [2.4 单词词汇表 (vocabularies)](#24-单词词汇表-vocabularies)
  - [2.6 字幕解析信息表 (subtitle_analysis)](#26-字幕解析信息表-subtitle_analysis)
  - [2.7 学习进度表 (user_progress)](#27-学习进度表-user_progress)
  - [2.8 单词学习记录表 (word_records)](#28-单词学习记录表-word_records)
  - [2.9 每日学习统计表 (daily_stats)](#29-每日学习统计表-daily_stats)
- [3. 数据关系图](#3-数据关系图)
- [4. 设计优化说明](#4-设计优化说明)
  - [4.1 表结构简化](#41-表结构简化)
  - [4.2 索引优化](#42-索引优化)
  - [4.3 性能考虑](#43-性能考虑)
- [5. 数据完整性约束](#5-数据完整性约束)
  - [5.1 必填字段](#51-必填字段)
  - [5.2 唯一约束](#52-唯一约束)
  - [5.3 引用完整性](#53-引用完整性)
- [6. 艾宾浩斯记忆曲线算法设计](#6-艾宾浩斯记忆曲线算法设计)
  - [6.1 记忆等级定义](#61-记忆等级定义)
  - [6.2 复习间隔算法](#62-复习间隔算法)
  - [6.3 学习流程](#63-学习流程)
  - [6.4 每日计划生成](#64-每日计划生成)
- [7. 索引设计优化](#7-索引设计优化)
  - [7.1 核心查询分析](#71-核心查询分析)
  - [7.2 复合索引设计](#72-复合索引设计)
  - [7.3 性能优化建议](#73-性能优化建议)

## 1. 数据库架构概述

### 1.1 设计原则

- **简洁性**: 精简表结构，避免过度设计
- **高效性**: 优化查询性能，合理设置索引
- **扩展性**: 支持功能扩展，保持向前兼容
- **一致性**: 统一命名规范和数据类型

### 1.2 技术架构

- **数据库**: 微信云数据库 (MongoDB)
- **数据类型**: 统一使用字符串 ID，简化时间处理
- **索引策略**: 仅保留核心业务查询索引

## 2. 核心数据表设计

### 2.1 用户信息表 (users)

**功能**: 存储用户基本信息、学习偏好和统计数据

```javascript
{
  _id: string,              // 微信openid (主键)
  user_id: number,          // 用户数字ID (唯一，显示用)
  nickname: string,         // 用户昵称
  avatar_url: string,       // 头像URL
  
  // 阅读设置
  reading_settings: {
    subtitle_lang: string,    // 字幕语言: 中英双语/仅英文/仅中文
    playback_speed: number    // 播放速度: 0.5/0.75/1.0/1.25/1.5/2.0
  },
  
  // 学习设置
  learning_settings: {
    voice_type: string,       // 语音类型: 美式发音/英式发音
    daily_word_limit: number  // 每日新词最大数量: 10/15/20/25/30/40/50
  },
  
  created_at: number,           // 创建时间戳（毫秒）
  updated_at: number            // 更新时间戳（毫秒）
}
```

**索引设计**:

```javascript
[
  { _id: 1 }, // 主键索引 (openid)
  { user_id: 1 }, // 用户ID查询 (唯一)
  { created_at: -1 }, // 注册时间查询
  { updated_at: -1 }, // 活跃度查询
];
```

### 2.2 书籍信息表 (books)

**功能**: 存储书籍基本信息和元数据

```javascript
{
  _id: string,              // 书籍ID (主键)
  title: string,            // 书名
  author: string,           // 作者
  cover_url: string,        // 封面图URL
  cover_md5: string,        // 封面图md5
  category: string,         // 分类 (literature/business/script/news)
  description: string,      // 描述
  difficulty: string,       // 难度 (easy/medium/hard)
  total_chapters: number,   // 总章节数
  total_duration: number,   // 音频时长
  is_active: boolean,       // 是否上架
  tags: string[],           // 标签数组

  // 简化元数据
  created_at: number,           // 创建时间戳（毫秒）
  updated_at: number            // 更新时间戳（毫秒）
}
```

**索引设计**:

```javascript
[
  { _id: 1 }, // 主键索引
  { category: 1, is_active: 1 }, // 分类筛选
  { difficulty: 1, category: 1 }, // 难度筛选
  { is_active: 1, created_at: -1 }, // 上架时间排序
  { tags: 1 }, // 标签查询
];
```

### 2.3 章节内容表 (chapters)

**功能**: 存储书籍章节内容

```javascript
{
  _id: string,               // 章节ID (主键)
  book_id: string,           // 所属书籍ID
  chapter_number: number,    // 章节序号
  title: string,             // 章节标题
  subtitle_url: string,      // 字幕路径
  subtitle_md5: string,      // 字幕文件md5
  audio_url: string,         // 音频路径
  audio_md5: string,         // 音频文件md5
  duration: number,          // 音频时长
  is_active: boolean,        // 是否启用

  created_at: number,           // 创建时间戳（毫秒）
  updated_at: number            // 更新时间戳（毫秒）
}
```

**索引设计**:

```javascript
[
  { _id: 1 }, // 主键索引
  { book_id: 1, chapter_number: 1 }, // 书籍章节查询
  { book_id: 1, is_active: 1 }, // 活跃章节查询
];
```

### 2.4 单词词汇表 (vocabularies)

**功能**: 存储单词详细信息

```javascript
{
  _id: string,              // 单词ID (主键)
  word: string,             // 单词 (唯一)
  phonetic_uk: string,      // 音标(英式)
  phonetic_us: string,      // 音标(美式)

  // 翻译对象数组
  translation: [{
    type: string,           // 词性 (如: "n.", "v.")
    meaning: string,        // 中文含义
    example: string         // 例句 (可选)
  }],

  tags: string[],           // 标签数组 (如: ["zk", "gk", "cet4"])

  // 词形变化对象数组
  exchange: [{
    type: string,           // 变化类型 (如: "p", "d", "i")
    form: string            // 变化形式
  }],

  bnc: number,              // BNC词频
  frq: number,              // 频率值
  audio_url_uk: string,     // 发音音频URL(英式)
  audio_url_us: string,     // 发音音频URL(美式)

  created_at: number,           // 创建时间戳（毫秒）
  updated_at: number            // 更新时间戳（毫秒）
}
```

**索引设计**:

```javascript
[
  { _id: 1 }, // 主键索引
  { word: 1 }, // 单词查询 (唯一)
  { tags: 1 }, // 标签查询
  { bnc: -1 }, // 词频排序
];
```

### 2.6 字幕解析信息表 (subtitle_analysis)

**功能**: 存储AI解析的字幕语言学习信息，为每行字幕提供详细的语法、单词、短语分析

```javascript
{
  _id: string,                    // 解析记录ID (book_id-article_id-subtitle_index)
  book_id: string,                // 书籍ID
  article_id: string,             // 章节ID (关联chapters表)
  subtitle_index: number,         // 字幕索引 (1, 2, 3, ...)
  english_text: string,           // 英文原文
  translation: string,            // 中文翻译
  sentence_structure: string,     // 句子结构分析

  // 重点单词数组
  key_words: [{
    word: string,                 // 单词
    pos: string,                  // 词性 (如: "n.", "v.", "adj.")
    meaning: string,              // 中文含义
    pronunciation: string         // 音标
  }],

  // 固定短语数组
  fixed_phrases: [{
    phrase: string,               // 固定短语
    meaning: string               // 中文含义
  }],

  // 核心语法点数组
  core_grammar: [{
    point: string,                // 语法点名称
    explanation: string           // 详细解释
  }],

  // 口语表达数组
  colloquial_expression: [{
    formal: string,               // 正式表达
    informal: string,             // 非正式/口语表达
    explanation: string           // 解释说明
  }],

  created_at: number,             // 创建时间戳（毫秒）
  updated_at: number              // 更新时间戳（毫秒）
}
```

**索引设计**:

```javascript
[
  { _id: 1 }, // 主键索引
  { book_id: 1, article_id: 1, subtitle_index: 1 }, // 主要业务查询（唯一）
  { book_id: 1 }, // 书籍查询
  { article_id: 1 }, // 章节查询
  { book_id: 1, article_id: 1 }, // 书籍章节查询
  { subtitle_index: 1 }, // 字幕索引查询
  { created_at: -1 }, // 创建时间查询
];
```

**数据示例**:

```javascript
{
  _id: "peter-001_PETER_BREAKS_THROUGH-1",
  book_id: "peter",
  article_id: "001_PETER_BREAKS_THROUGH",
  subtitle_index: 1,
  english_text: "All children, except one, grow up.",
  translation: "所有的孩子都会长大，除了一个。",
  sentence_structure: "主语(All children) + 插入语(except one) + 谓语(grow up)",
  key_words: [
    {
      word: "children",
      pos: "n.",
      meaning: "孩子们",
      pronunciation: "/ˈtʃɪldrən/"
    },
    {
      word: "grow",
      pos: "v.",
      meaning: "成长，长大",
      pronunciation: "/ɡroʊ/"
    }
  ],
  fixed_phrases: [
    {
      phrase: "grow up",
      meaning: "长大，成长"
    }
  ],
  core_grammar: [
    {
      point: "一般现在时",
      explanation: "表示普遍真理或客观事实，所有孩子都会长大是自然规律"
    },
    {
      point: "插入语",
      explanation: "'except one'作为插入语，起到补充说明的作用，暗示了故事的特殊性"
    }
  ],
  colloquial_expression: [],
  created_at: 1703232000000,
  updated_at: 1703232000000
}
```

**查询示例**:

```javascript
// 获取某本书某篇文章的所有字幕解析
db.subtitle_analysis.find({ 
  book_id: "peter", 
  article_id: "001_PETER_BREAKS_THROUGH" 
}).sort({ subtitle_index: 1 })

// 获取特定字幕的解析信息
db.subtitle_analysis.findOne({ 
  book_id: "peter",
  article_id: "001_PETER_BREAKS_THROUGH", 
  subtitle_index: 1 
})

// 获取某本书的所有解析数据
db.subtitle_analysis.find({ book_id: "peter" }).sort({ article_id: 1, subtitle_index: 1 })
```

### 2.7 学习进度表 (user_progress)

**功能**: 记录用户对各书籍的学习进度

```javascript
{
  _id: string,                  // 进度ID (userId_bookId)
  user_id: string,              // 用户ID
  book_id: string,              // 书籍ID
  current_chapter: number,      // 当前章节序号

  // 章节进度详情 - 记录每个章节的播放时间和完成状态
  chapter_progress: {
    [chapter_id]: {
      time: number,             // 当前播放时间(秒)
      completed: boolean        // 是否完成
    }
  },

  created_at: number,           // 创建时间戳（毫秒）
  updated_at: number            // 更新时间戳（毫秒）
}
```

**索引设计**:

```javascript
[
  { _id: 1 }, // 主键索引
  { user_id: 1, updated_at: -1 }, // 用户最近学习查询
  { user_id: 1 }, // 用户查询
];
```

### 2.7 单词学习记录表 (word_records)

**功能**: 记录用户单词学习状态，专为艾宾浩斯记忆曲线优化

```javascript
{
  _id: string,              // 记录ID (user_id_word_id)
  user_id: string,          // 用户ID
  word_id: string,          // 单词ID
  source_book_id: string,   // 书籍id
  source_chapter_id: string, // 章节id

  // 学习和复习管理 (核心)
  level: number,                    // 记忆等级 0-6 (null未学习, 0=新词, 1-5=复习阶段, 6=已掌握)
  first_learn_date: string,         // 首次学习日期
  next_review_date: string,         // 下次复习日期 (艾宾浩斯间隔)
  actual_review_dates: []string,    // 实际复习日期
  actual_learn_dates: []string,     // 实际学习日期（记录每次重新学习）

  created_at: number,               // 创建时间戳（毫秒）
  updated_at: number                // 更新时间戳（毫秒）
}
```

**索引设计**:

```javascript
[
  { _id: 1 }, // 主键索引
  { user_id: 1, next_review_at: 1 }, // 复习计划查询
  { user_id: 1, level: 1 }, // 按掌握程度查询
];
```

### 2.9 每日学习统计表 (daily_stats)

**功能**: 记录用户每日学习统计数据，用于生成 GitHub 风格的学习日历

```javascript
{
  _id: string,              // 统计ID (user_id_date)
  user_id: string,          // 用户ID
  date: string,             // 统计日期 (YYYY-MM-DD格式)

  // 学习统计
  learned_count: number,    // 当日学习新单词数
  reviewed_count: number,   // 当日复习单词数

  created_at: number,       // 创建时间戳（毫秒）
  updated_at: number        // 更新时间戳（毫秒）
}
```

**索引设计**:

```javascript
[
  { _id: 1 }, // 主键索引
  { user_id: 1, date: -1 }, // 用户日期查询
  { date: -1 }, // 全局日期统计
];
```

## 3. 数据关系图

```
users (用户)
├── user_progress (学习进度) ──→ books (书籍)
├── word_records (单词记录) ──→ vocabularies (单词)

books (书籍)
├── chapters (章节)
└── subtitle_analysis (字幕解析) ──→ chapters (章节)
```

## 4. 设计优化说明

### 4.1 表结构简化

1. **合并相关表**: 将用户偏好和统计信息合并到用户表中
2. **简化字段类型**: 统一使用字符串 ID，简化时间字段
3. **减少冗余**: 移除不必要的字段和关系

### 4.2 索引优化

- **仅保留核心索引**: 只为高频查询创建索引
- **复合索引优化**: 合理设计复合索引顺序
- **避免过度索引**: 平衡查询性能和写入性能

### 4.3 性能考虑

1. **查询优化**: 支持分页、筛选、排序等常用查询
2. **数据分离**: 内容和用户数据分离，便于缓存
3. **批量操作**: 支持批量更新用户学习记录

## 5. 数据完整性约束

### 5.1 必填字段

- 所有表的 `_id`、`created_at`、`updated_at` 为必填
- 用户表的 `nickname` 为必填
- 书籍表的 `title`、`author`、`category` 为必填
- 单词表的 `word`、`translations` 为必填

### 5.2 唯一约束

- `users._id` (openid)
- `vocabularies.word` (单词唯一)
- `user_progress._id` (user_id_book_id)
- `word_records._id` (user_id_word_id)
- `daily_plans._id` (user_id_plan_date)

### 5.3 引用完整性

- 所有 `user_id` 必须存在于 `users` 表中
- 所有 `book_id` 必须存在于 `books` 表中
- 所有 `word_id` 必须存在于 `vocabularies` 表中

## 6. 艾宾浩斯记忆曲线算法设计

### 6.1 记忆等级定义

- `level: 0` - 新词，从未学习
- `level: 1-6` - 复习阶段，对应不同的复习间隔
- `level: 7` - 已掌握，无需频繁复习

### 6.2 复习间隔算法

```
复习间隔 = base_interval * (2 ^ (level - 1)) * random_factor
其中：
- base_interval = 1天 (基础间隔)
- random_factor = 0.8-1.2 (随机因子，增加个性化)
```

### 6.3 学习流程

1. **新学单词**: `level = 0` → `level = 1`, 设置 `next_review_at = 当前时间 + 1天`
2. **答对**: `level += 1`, 增加 `correct_count`, 延长 `next_review_at`
3. **答错**: `level = max(1, level - 1)`, 重置 `correct_count = 0`, 缩短复习间隔
4. **掌握条件**: `level >= 7 且 correct_count >= 3`

### 6.4 每日计划生成

1. 查询 `next_review_at <= 今天` 的单词作为 `review_words`
2. 根据 `target_new_count` 从词库中选择新词作为 `new_words`
3. 创建或更新当日的 `daily_plans` 记录

## 7. 索引设计优化

### 7.1 核心查询分析

基于代码实际使用情况，识别出以下高频查询模式：

#### word_records 表查询模式
1. **学习统计查询**: `user_id + first_learn_date`
2. **复习列表查询**: `user_id + level + next_review_date` 
3. **逾期单词查询**: `user_id + level + next_review_date`
4. **单词状态查询**: `user_id + word_id`

#### daily_stats 表查询模式
1. **日期范围统计**: `user_id + date`
2. **单日统计查询**: `user_id + date`（唯一）

### 7.2 复合索引设计

#### word_records 表索引优化
```javascript
[
  // 核心业务查询索引
  { user_id: 1, word_id: 1 },                    // 单词状态查询（唯一，防越权）
  { user_id: 1, level: 1, next_review_date: 1 }, // 复习队列查询
  { user_id: 1, first_learn_date: 1, level: 1 }, // 学习统计查询
  
  // 专项查询索引  
  { user_id: 1, level: 1 },                      // 按掌握程度筛选
  { user_id: 1, created_at: 1 },                 // 新词排序查询
  
  // 系统管理索引
  { updated_at: -1 },                            // 数据维护查询
]
```

#### daily_stats 表索引优化
```javascript
[
  // 核心业务查询索引
  { user_id: 1, date: 1 },      // 日期统计查询（唯一）
  { user_id: 1, date: -1 },     // 时间序列查询
  
  // 全局统计索引
  { date: -1 },                 // 全局日期统计
  { date: 1, user_id: 1 },      // 分页查询优化
]
```

#### vocabularies 表索引保持
```javascript
[
  { _id: 1 },      // 主键索引
  { word: 1 },     // 单词查询（唯一）
  { tags: 1 },     // 标签筛选
  { bnc: -1 },     // 频率排序
]
```

### 7.3 性能优化建议

#### 查询优化策略
1. **复合索引顺序**: 高选择性字段优先（user_id → 业务字段）
2. **覆盖索引**: 减少回表查询，提升性能
3. **分页优化**: 使用稳定排序字段避免分页漂移

#### 写入优化考虑
1. **索引数量平衡**: 避免过度索引影响写入性能
2. **批量操作**: 使用事务进行批量更新
3. **异步统计**: 使用后台任务更新daily_stats

#### 监控指标
- 查询响应时间 < 100ms
- 索引命中率 > 95%
- 慢查询日志监控

### 7.4 安全性增强

#### 权限控制索引
所有用户相关查询都基于 `user_id` 字段，确保：
1. **防止越权**: 用户只能访问自己的数据
2. **查询隔离**: 多租户数据天然隔离
3. **性能保证**: user_id 作为索引前缀保证查询效率

#### 数据完整性
- 使用复合唯一索引防止重复数据
- 外键约束通过应用层逻辑保证
- 定期数据一致性检查

这个优化后的数据库设计专为艾宾浩斯记忆曲线算法优化，结构简洁且高效，更适合小程序的快速开发和维护需求。
