# 英语学习小程序数据库设计文档

## 1. 数据库架构概述

### 1.1 设计原则

- **简洁性**: 精简表结构，避免过度设计
- **高效性**: 优化查询性能，合理设置索引
- **扩展性**: 支持功能扩展，保持向前兼容
- **一致性**: 统一命名规范和数据类型

### 1.2 技术架构

- **数据库**: 微信云数据库 (MongoDB)
- **数据类型**: 统一使用字符串ID，简化时间处理
- **索引策略**: 仅保留核心业务查询索引

## 2. 核心数据表设计

### 2.1 用户信息表 (users)

**功能**: 存储用户基本信息、学习偏好和统计数据

```javascript
{
  _id: string,              // 微信openid (主键)
  nickname: string,         // 用户昵称
  avatar: string,           // 头像URL
  level: number,            // 用户等级 (1-10)
  study_days: number,       // 连续学习天数
  total_study_time: number, // 总学习时长(秒)
  
  // 学习偏好 (合并到用户表)
  display_mode: string,     // 显示模式 (both/chinese-mask/english-mask)
  
  // 统计信息 (合并到用户表)
  total_words: number,      // 学习过的总单词数
  mastered_words: number,   // 已掌握单词数  
  
  created_at: Date,
  last_login_at: Date,
  updated_at: Date
}
```

**索引设计**:
```javascript
[
  { _id: 1 },                        // 主键索引
  { level: -1 },                     // 等级查询
  { last_login_at: -1 }              // 活跃度查询
]
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
  created_at: Date,
  updated_at: Date
}
```

**索引设计**:
```javascript
[
  { _id: 1 },                         // 主键索引
  { category: 1, is_active: 1 },       // 分类筛选
  { difficulty: 1, category: 1 },     // 难度筛选
  { is_active: 1, created_at: -1 },   // 上架时间排序
  { tags: 1 }                         // 标签查询
]
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
  
  created_at: Date,
  updated_at: Date
}
```

**索引设计**:
```javascript
[
  { _id: 1 },                      // 主键索引
  { book_id: 1, chapter_number: 1 }, // 书籍章节查询
  { book_id: 1, is_active: 1 }       // 活跃章节查询
]
```

### 2.4 单词词汇表 (vocabularies)

**功能**: 存储单词详细信息

```javascript
{
  _id: string,              // 单词ID (主键)
  word: string,             // 单词 (唯一)
  phonetic: string,         // 音标
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
  audio_url: string,        // 发音音频URL
  audio_url_uk: string,     // 发音音频URL(英式)
  audio_url_us: string,     // 发音音频URL(美式)
  
  created_at: Date,
  updated_at: Date
}
```

**索引设计**:
```javascript
[
  { _id: 1 },                         // 主键索引
  { word: 1 },                        // 单词查询 (唯一)
  { tags: 1 },                        // 标签查询
  { bnc: -1 }                         // 词频排序
]
```

### 2.5 章节单词关联表 (chapter_vocabularies)

**功能**: 记录每个章节包含的单词及其在章节中的重要性

```javascript
{
  _id: string,              // 关联ID (book_id_chapter_id_word)
  book_id: string,          // 书籍ID
  chapter_id: string,       // 章节ID  
  word_list: []string       // 单词列表
  word_info_list: []string  // 单词信息列表 "{word},{tags},{frq},{collins},{oxford}"
  created_at: Date
}
```

**索引设计**:
```javascript
[
  { _id: 1 },                         // 主键索引
  { chapter_id: 1 },                  // 章节单词查询
  { book_id: 1, chapter_id: 1 },      // 书籍章节查询
  { word: 1 }                         // 单词查询
]
```

### 2.6 学习进度表 (user_progress)

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
  
  created_at: Date,
  updated_at: Date
}
```

**索引设计**:
```javascript
[
  { _id: 1 },                       // 主键索引
  { user_id: 1, updated_at: -1 },   // 用户最近学习查询
  { user_id: 1 }                    // 用户查询
]
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
  level: number,                    // 记忆等级 0-7 (0=新词, 1-6=复习阶段, 7=已掌握)
  first_learn_date: string,         // 首次学习日期
  next_review_date: string,         // 下次复习日期 (艾宾浩斯间隔) 
  actual_review_dates: []string,    // 实际复习日期
}
```

**索引设计**:
```javascript
[
  { _id: 1 },                        // 主键索引
  { user_id: 1, next_review_at: 1 }, // 复习计划查询
  { user_id: 1, level: 1 }           // 按掌握程度查询
]
```

**索引设计**:
```javascript
[
  { _id: 1 },                        // 主键索引
  { user_id: 1, plan_date: -1 },     // 用户计划历史
  { user_id: 1, completed: 1 }       // 完成状态查询
]
```

## 3. 数据关系图

```
users (用户) 
├── user_progress (学习进度) ──→ books (书籍)
├── word_records (单词记录) ──→ vocabularies (单词)

books (书籍)
├── chapters (章节)
└── chapter_vocabularies (章节单词) ──→ vocabularies (单词)
```

## 4. 设计优化说明

### 4.1 表结构简化

1. **合并相关表**: 将用户偏好和统计信息合并到用户表中
2. **简化字段类型**: 统一使用字符串ID，简化时间字段
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

这个优化后的数据库设计专为艾宾浩斯记忆曲线算法优化，结构简洁且高效，更适合小程序的快速开发和维护需求。