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
  totalPoints: number,      // 总积分
  studyDays: number,        // 连续学习天数
  totalStudyTime: number,   // 总学习时长(分钟)
  
  // 学习偏好 (合并到用户表)
  displayMode: string,      // 显示模式 (both/chinese-mask/english-mask)
  dailyGoal: number,        // 每日目标单词数 (默认20)
  autoPlay: boolean,        // 自动播放发音 (默认true)
  
  // 统计信息 (合并到用户表)
  totalWords: number,       // 学习过的总单词数
  masteredWords: number,    // 已掌握单词数  
  booksCompleted: number,   // 完成的书籍数
  averageAccuracy: number,  // 平均正确率
  
  createdAt: Date,
  lastLoginAt: Date,
  updatedAt: Date
}
```

**索引设计**:
```javascript
[
  { _id: 1 },                        // 主键索引
  { level: -1, totalPoints: -1 },    // 排行榜查询
  { lastLoginAt: -1 }                // 活跃度查询
]
```

### 2.2 书籍信息表 (books)

**功能**: 存储书籍基本信息和元数据

```javascript
{
  _id: string,              // 书籍ID (主键)
  title: string,            // 书名
  author: string,           // 作者
  cover: string,            // 封面图URL
  category: string,         // 分类 (literature/business/script/news)
  description: string,      // 描述
  difficulty: string,       // 难度 (easy/medium/hard)
  totalChapters: number,    // 总章节数
  estimatedTime: number,    // 预估学习时长(分钟)
  vocabularyCount: number,  // 词汇量
  popularity: number,       // 受欢迎程度 (0-100)
  isActive: boolean,        // 是否上架
  tags: string[],           // 标签数组
  
  // 简化元数据
  publisher: string,        // 出版社
  publishDate: string,      // 出版日期 (YYYY-MM-DD)
  
  createdAt: Date,
  updatedAt: Date
}
```

**索引设计**:
```javascript
[
  { _id: 1 },                         // 主键索引
  { category: 1, isActive: 1 },       // 分类筛选
  { difficulty: 1, category: 1 },     // 难度筛选
  { popularity: -1, isActive: 1 },    // 热门排序
  { tags: 1 }                         // 标签查询
]
```

### 2.3 章节内容表 (chapters)

**功能**: 存储书籍章节内容

```javascript
{
  _id: string,              // 章节ID (主键)
  bookId: string,           // 所属书籍ID
  chapterNumber: number,    // 章节序号
  title: string,            // 章节标题
  content: string,          // 章节内容 (纯文本)
  wordIds: string[],        // 关联单词ID列表
  estimatedTime: number,    // 预估阅读时长(分钟)
  wordCount: number,        // 单词数
  isActive: boolean,        // 是否启用
  
  createdAt: Date,
  updatedAt: Date
}
```

**索引设计**:
```javascript
[
  { _id: 1 },                      // 主键索引
  { bookId: 1, chapterNumber: 1 }, // 书籍章节查询
  { bookId: 1, isActive: 1 }       // 活跃章节查询
]
```

### 2.4 单词词汇表 (vocabularies)

**功能**: 存储单词详细信息

```javascript
{
  _id: string,              // 单词ID (主键)
  word: string,             // 单词 (唯一)
  phonetic: string,         // 音标
  
  // 优化翻译结构 (简化为数组)
  translations: [{
    type: string,           // 词性 (n./v./adj./adv.)
    meaning: string,        // 中文含义
    example: string         // 例句 (可选)
  }],
  
  difficulty: string,       // 难度 (easy/medium/hard)
  frequency: string,        // 使用频率 (high/medium/low) 
  audioUrl: string,         // 发音音频URL
  bookIds: string[],        // 关联书籍ID列表
  
  // 相关词汇 (可选)
  synonyms: string[],       // 同义词
  antonyms: string[],       // 反义词
  
  createdAt: Date,
  updatedAt: Date
}
```

**索引设计**:
```javascript
[
  { _id: 1 },                         // 主键索引
  { word: 1 },                        // 单词查询 (唯一)
  { difficulty: 1, frequency: 1 },    // 难度频率筛选
  { bookIds: 1 }                      // 书籍关联查询
]
```

### 2.5 学习进度表 (user_progress)

**功能**: 记录用户对各书籍的学习进度

```javascript
{
  _id: string,              // 进度ID (userId_bookId)
  userId: string,           // 用户ID
  bookId: string,           // 书籍ID
  currentChapter: number,   // 当前章节
  progress: number,         // 进度百分比(0-100)
  studyTime: number,        // 累计学习时长(分钟)
  status: string,           // 学习状态 (studying/completed/paused)
  chaptersCompleted: number[], // 已完成章节列表
  
  startedAt: Date,          // 开始学习时间
  lastStudyAt: Date,        // 最后学习时间
  completedAt: Date,        // 完成时间 (可选)
  createdAt: Date,
  updatedAt: Date
}
```

**索引设计**:
```javascript
[
  { _id: 1 },                       // 主键索引
  { userId: 1, lastStudyAt: -1 },   // 用户最近学习查询
  { userId: 1, status: 1 }          // 用户状态筛选
]
```

### 2.6 单词学习记录表 (word_records)

**功能**: 记录用户对单词的学习情况，支持艾宾浩斯遗忘曲线

```javascript
{
  _id: string,              // 记录ID (userId_wordId)
  userId: string,           // 用户ID
  wordId: string,           // 单词ID
  status: string,           // 学习状态 (new/learning/mastered)
  
  // 学习统计 (简化)
  correctCount: number,     // 答对次数
  totalCount: number,       // 总测试次数
  accuracy: number,         // 正确率 (0-100)
  
  // 时间记录
  firstStudyAt: Date,       // 首次学习时间
  lastStudyAt: Date,        // 最后学习时间
  masteredAt: Date,         // 掌握时间 (可选)
  nextReviewAt: Date,       // 下次复习时间
  
  // 复习管理 (艾宾浩斯)
  reviewLevel: number,      // 复习等级 (1-7)
  studyCount: number,       // 学习次数
  source: string,           // 学习来源 (book/daily/review)
  
  createdAt: Date,
  updatedAt: Date
}
```

**索引设计**:
```javascript
[
  { _id: 1 },                        // 主键索引
  { userId: 1, status: 1 },          // 用户状态查询
  { userId: 1, nextReviewAt: 1 },    // 复习时间查询
  { userId: 1, lastStudyAt: -1 }     // 最近学习查询
]
```

### 2.7 每日学习计划表 (daily_plans)

**功能**: 存储每日学习计划配置

```javascript
{
  _id: string,              // 计划ID (date)
  date: string,             // 日期 YYYY-MM-DD
  dayKey: string,           // 天数标识 day1/day2...
  title: string,            // 计划标题
  description: string,      // 计划描述
  totalWords: number,       // 当天总单词数
  wordIds: string[],        // 单词ID列表
  targetTime: number,       // 目标学习时长(分钟)
  difficulty: string,       // 整体难度
  isActive: boolean,        // 是否启用
  
  createdAt: Date,
  updatedAt: Date
}
```

**索引设计**:
```javascript
[
  { _id: 1 },               // 主键索引
  { date: -1 },             // 日期查询
  { isActive: 1, date: -1 } // 活跃计划查询
]
```

## 3. 数据关系图

```
users (用户) 
├── user_progress (学习进度) ──→ books (书籍)
├── word_records (单词记录) ──→ vocabularies (单词)
└── daily_plans (每日计划) ──→ vocabularies (单词)

books (书籍)
└── chapters (章节) ──→ vocabularies (单词)
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
- 所有表的 `_id`、`createdAt`、`updatedAt` 为必填
- 用户表的 `nickname` 为必填
- 书籍表的 `title`、`author`、`category` 为必填
- 单词表的 `word`、`translations` 为必填

### 5.2 唯一约束
- `users._id` (openid)
- `vocabularies.word` (单词唯一)
- `user_progress._id` (userId_bookId)
- `word_records._id` (userId_wordId)

### 5.3 引用完整性
- 所有 `userId` 必须存在于 `users` 表中
- 所有 `bookId` 必须存在于 `books` 表中  
- 所有 `wordId` 必须存在于 `vocabularies` 表中

这个优化后的数据库设计既简化了结构，又保持了完整的功能支持，更适合小程序的快速开发和维护需求。