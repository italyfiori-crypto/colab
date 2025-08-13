# 英语学习小程序后端接口设计方案

## 项目概述

这是一个基于微信云开发平台的英语学习小程序项目，主要功能包括书籍阅读、单词学习、进度跟踪等。本文档详细描述了后端接口设计方案、数据结构设计、性能优化策略等技术方案。

## 1. 整体架构设计

### 1.1 系统架构图

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   微信小程序端   │ ──▶│   微信云开发     │ ──▶│   云数据库      │
│   (前端交互)     │    │   (云函数API)   │    │   (数据存储)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                               │
                               ▼
                       ┌─────────────────┐
                       │   Redis缓存     │
                       │   (性能优化)    │
                       └─────────────────┘
```

### 1.2 技术栈选型

- **前端**: 微信小程序原生框架
- **后端**: 微信云开发 + Node.js云函数
- **数据库**: 微信云数据库 (MongoDB)
- **缓存**: Redis (如支持) 或内存缓存
- **存储**: 微信云存储
- **实时通信**: 微信云开发实时数据库

### 1.3 模块化设计

```
cloudfunctions/
├── api/                    # API接口模块
│   ├── user/              # 用户相关接口
│   ├── content/           # 内容管理接口
│   ├── vocabulary/        # 单词学习接口
│   └── study/             # 学习记录接口
├── database/              # 数据库模块
│   ├── models/            # 数据模型
│   ├── utils/             # 数据库工具
│   └── init.js            # 数据库初始化
├── utils/                 # 通用工具模块
│   ├── cache.js           # 缓存工具
│   ├── validator.js       # 数据验证
│   └── logger.js          # 日志记录
└── main/                  # 主函数入口
    └── index.js           # 路由分发
```

## 2. 数据库设计

本项目的数据库设计已独立成册，详细的表结构、索引设计和关系图请参考：

📋 **[数据库设计文档](./database-design.md)**

### 2.1 核心表概览

| 表名 | 功能描述 | 主要字段 |
|------|----------|----------|
| `users` | 用户信息、偏好和统计 | openid, nickname, level, totalPoints, studyDays |
| `books` | 书籍基本信息 | title, author, category, difficulty, popularity |
| `chapters` | 章节内容 | bookId, title, content, wordIds |
| `vocabularies` | 单词词汇 | word, phonetic, translations, difficulty |
| `user_progress` | 学习进度 | userId, bookId, progress, currentChapter |
| `word_records` | 单词学习记录 | userId, wordId, status, accuracy, reviewLevel |
| `daily_plans` | 每日学习计划 | date, wordIds, targetTime, difficulty |

### 2.2 设计特点

- **简化结构**: 从8个表精简到7个核心表
- **统一ID**: 使用字符串ID，简化数据处理
- **合并字段**: 将相关属性合并到主表中
- **优化索引**: 仅保留核心业务查询的索引

详细的表结构定义、字段说明、索引策略和数据关系图请查看数据库设计文档。

## 3. 接口设计方案

### 3.1 API规范

#### 3.1.1 统一响应格式

```javascript
// 成功响应
{
  success: true,
  data: any,                // 响应数据
  message?: string,         // 成功消息
  timestamp: number         // 时间戳
}

// 错误响应
{
  success: false,
  error: {
    code: string,           // 错误代码
    message: string,        // 错误消息
    details?: any          // 错误详情
  },
  timestamp: number
}
```

#### 3.1.2 分页响应格式

```javascript
{
  success: true,
  data: {
    items: Array,           // 数据列表
    pagination: {
      page: number,         // 当前页码
      limit: number,        // 每页数量
      total: number,        // 总数量
      totalPages: number,   // 总页数
      hasNext: boolean,     // 是否有下一页
      hasPrev: boolean      // 是否有上一页
    }
  }
}
```

### 3.2 用户相关接口

#### 3.2.1 用户登录/注册

```javascript
POST /api/user/login
Content-Type: application/json

Request Body:
{
  code: string,             // 微信登录code
  userInfo?: {              // 用户信息 (可选)
    nickname: string,
    avatar: string
  }
}

Response:
{
  success: true,
  data: {
    openid: string,         // 用户openid
    token: string,          // 访问令牌
    user: UserInfo,         // 用户信息
    isNewUser: boolean      // 是否新用户
  }
}
```

#### 3.2.2 获取用户信息和统计

```javascript
GET /api/user/profile
Authorization: Bearer {token}

Response:
{
  success: true,
  data: {
    user: UserInfo,         // 用户基本信息
    statistics: {           // 学习统计
      totalWords: number,   // 学习过的总单词数
      masteredWords: number, // 已掌握单词数
      studyDays: number,    // 连续学习天数
      totalTime: number,    // 总学习时长(分钟)
      currentLevel: number, // 当前等级
      currentPoints: number, // 当前积分
      accuracy: number,     // 平均正确率
      booksCompleted: number // 完成书籍数
    },
    recentProgress: [{      // 最近学习进度
      bookId: number,
      bookTitle: string,
      progress: number,
      lastStudyAt: Date
    }],
    achievements: [{        // 成就列表
      id: string,
      name: string,
      description: string,
      unlockedAt: Date
    }]
  }
}
```

#### 3.2.3 更新用户信息

```javascript
PUT /api/user/profile
Authorization: Bearer {token}
Content-Type: application/json

Request Body:
{
  nickname?: string,        // 昵称
  avatar?: string,          // 头像
  preferences?: {           // 学习偏好
    displayMode?: string,
    dailyGoal?: number,
    reminderTime?: string,
    autoPlay?: boolean
  }
}

Response:
{
  success: true,
  data: {
    user: UserInfo          // 更新后的用户信息
  }
}
```

### 3.3 内容管理接口

#### 3.3.1 首页数据合并接口 (性能优化核心)

```javascript
GET /api/home/data
Authorization: Bearer {token}
Query Parameters:
- refresh?: boolean       // 是否强制刷新缓存

Response:
{
  success: true,
  data: {
    recentBooks: [{         // 最近学习的书籍
      id: number,
      title: string,
      author: string,
      cover: string,
      progress: number,     // 学习进度
      lastStudyAt: Date
    }],
    categories: [{          // 分类列表及统计
      id: string,
      name: string,
      count: number,        // 书籍数量
      active: boolean
    }],
    recommendBooks: [{      // 推荐书籍
      id: number,
      title: string,
      author: string,
      cover: string,
      category: string,
      difficulty: string,
      popularity: number,
      reason: string        // 推荐理由
    }],
    dailyPlan: {            // 今日学习计划
      date: string,
      dayKey: string,
      title: string,
      totalWords: number,
      completedWords: number,
      progress: number
    },
    userStats: {            // 用户统计快照
      level: number,
      points: number,
      studyDays: number,
      todayTime: number     // 今日学习时长
    },
    hotWords: [{            // 热门单词
      id: number,
      word: string,
      meaning: string,
      difficulty: string
    }]
  }
}
```

#### 3.3.2 书籍搜索和筛选

```javascript
GET /api/books/search
Authorization: Bearer {token}
Query Parameters:
- keyword?: string        // 搜索关键词
- category?: string       // 分类筛选
- difficulty?: string     // 难度筛选
- tags?: string[]         // 标签筛选
- sort?: string          // 排序方式 (popularity/difficulty/date)
- page?: number          // 页码 (默认1)
- limit?: number         // 每页数量 (默认20)

Response:
{
  success: true,
  data: {
    books: [{
      id: number,
      title: string,
      author: string,
      cover: string,
      category: string,
      difficulty: string,
      estimatedTime: number,
      vocabularyCount: number,
      popularity: number,
      tags: string[],
      userProgress?: {      // 用户学习进度 (如果有)
        progress: number,
        status: string
      }
    }],
    pagination: PaginationInfo,
    filters: {              // 可用筛选项
      categories: [{ value: string, label: string, count: number }],
      difficulties: [{ value: string, label: string, count: number }],
      tags: [{ value: string, label: string, count: number }]
    }
  }
}
```

#### 3.3.3 书籍详情

```javascript
GET /api/books/:bookId
Authorization: Bearer {token}

Response:
{
  success: true,
  data: {
    book: BookInfo,         // 书籍详细信息
    chapters: [{            // 章节列表
      id: number,
      chapterNumber: number,
      title: string,
      estimatedTime: number,
      wordCount: number,
      isCompleted: boolean  // 用户是否已完成
    }],
    userProgress: {         // 用户学习进度
      progress: number,
      currentChapter: number,
      studyTime: number,
      status: string,
      startedAt: Date,
      lastStudyAt: Date
    },
    statistics: {           // 书籍统计
      totalUsers: number,   // 学习用户数
      completionRate: number, // 完成率
      averageTime: number   // 平均学习时长
    },
    relatedBooks: [{        // 相关推荐
      id: number,
      title: string,
      cover: string,
      similarity: number    // 相似度
    }]
  }
}
```

#### 3.3.4 章节内容

```javascript
GET /api/chapters/:chapterId
Authorization: Bearer {token}

Response:
{
  success: true,
  data: {
    chapter: ChapterInfo,   // 章节详细信息
    vocabularies: [{        // 章节词汇
      id: number,
      word: string,
      phonetic: string,
      translations: Array,
      difficulty: string,
      userRecord?: {        // 用户学习记录
        status: string,
        accuracy: number,
        lastStudyAt: Date
      }
    }],
    navigation: {           // 导航信息
      prevChapter?: ChapterInfo,
      nextChapter?: ChapterInfo
    }
  }
}
```

### 3.4 单词学习接口 (核心功能)

#### 3.4.1 获取单词本数据

```javascript
GET /api/vocabulary/list
Authorization: Bearer {token}
Query Parameters:
- type: string            // 类型 (day|book|review|search)
- value: string           // 值 (day1/bookId/all/keyword)
- mode?: string          // 模式 (simple|detailed) 默认simple
- page?: number          // 页码
- limit?: number         // 数量限制

Response:
{
  success: true,
  data: {
    words: [{
      id: number,
      word: string,
      phonetic: string,
      translations: Array,
      difficulty: string,
      frequency: string,
      audioUrl?: string,
      examples?: Array,     // detailed模式包含
      userRecord: {         // 用户学习记录
        status: string,     // new/learning/mastered
        accuracy: number,
        studyCount: number,
        lastStudyAt: Date,
        reviewAt?: Date
      }
    }],
    statistics: {
      total: number,        // 总数
      mastered: number,     // 已掌握
      learning: number,     // 学习中
      new: number,          // 新单词
      accuracy: number      // 平均正确率
    },
    progress: number,       // 整体进度
    nextReviewTime?: Date,  // 下次复习时间
    pagination?: PaginationInfo
  }
}
```

#### 3.4.2 批量更新单词学习状态 (性能优化核心)

```javascript
POST /api/vocabulary/batch-update
Authorization: Bearer {token}
Content-Type: application/json

Request Body:
{
  sessionId: string,        // 学习会话ID
  updates: [{
    wordId: number,         // 单词ID
    action: string,         // 操作类型 (view/study/master/unfamiliar/test)
    timeSpent: number,      // 花费时间(秒)
    result?: {              // 学习结果 (可选)
      correct?: boolean,    // 是否正确
      answer?: string,      // 用户答案
      attempts?: number     // 尝试次数
    },
    timestamp: Date         // 操作时间
  }],
  context?: {               // 上下文信息
    source: string,         // 来源 (daily/book/review)
    bookId?: number,
    chapterId?: number
  }
}

Response:
{
  success: true,
  data: {
    updated: number,        // 成功更新数量
    failed: number,         // 失败数量
    points: number,         // 获得积分
    newMastered: number,    // 新掌握单词数
    achievements?: string[], // 解锁成就
    statistics: {           // 更新后统计
      mastered: number,
      learning: number,
      accuracy: number
    },
    errors?: [{             // 错误详情
      wordId: number,
      error: string
    }]
  }
}
```

#### 3.4.3 获取复习单词 (艾宾浩斯遗忘曲线)

```javascript
GET /api/vocabulary/review
Authorization: Bearer {token}
Query Parameters:
- limit?: number          // 数量限制 (默认20)
- priority?: string       // 优先级 (urgent/normal/all)
- difficulty?: string     // 难度筛选

Response:
{
  success: true,
  data: {
    words: [{
      id: number,
      word: string,
      phonetic: string,
      translations: Array,
      userRecord: {
        status: string,
        reviewLevel: number,  // 复习等级
        reviewAt: Date,       // 应复习时间
        lastStudyAt: Date,
        accuracy: number,
        priority: string      // urgent/normal
      }
    }],
    reviewInfo: {
      total: number,          // 总复习单词数
      urgent: number,         // 紧急复习 (过期)
      normal: number,         // 正常复习
      today: number,          // 今日应复习
      overdue: number         // 已过期
    },
    schedule: [{             // 复习计划
      date: string,
      count: number
    }]
  }
}
```

### 3.5 学习记录接口

#### 3.5.1 开始学习会话

```javascript
POST /api/study/start
Authorization: Bearer {token}
Content-Type: application/json

Request Body:
{
  type: string,             // 会话类型 (book/daily/review/test)
  bookId?: number,          // 书籍ID (书籍学习时必需)
  chapterId?: number,       // 章节ID (章节学习时必需)
  plan?: {                  // 学习计划 (可选)
    targetWords: number,    // 目标单词数
    targetTime: number      // 目标时间(分钟)
  }
}

Response:
{
  success: true,
  data: {
    sessionId: string,      // 会话ID
    startTime: Date,        // 开始时间
    plan: {                 // 学习计划
      words: Array,         // 计划学习单词
      estimatedTime: number, // 预估时间
      difficulty: string    // 整体难度
    },
    context: {              // 上下文信息
      book?: BookInfo,
      chapter?: ChapterInfo,
      userProgress?: Object
    }
  }
}
```

#### 3.5.2 结束学习会话

```javascript
POST /api/study/end
Authorization: Bearer {token}
Content-Type: application/json

Request Body:
{
  sessionId: string,        // 会话ID
  endTime: Date,           // 结束时间
  summary: {               // 学习总结
    totalTime: number,     // 总学习时长(秒)
    wordsStudied: number,  // 学习单词数
    correctAnswers: number, // 正确答案数
    rating?: number        // 用户评分 (1-5)
  }
}

Response:
{
  success: true,
  data: {
    session: {
      id: string,
      studyTime: number,    // 学习时长
      wordsLearned: number, // 新学单词数
      wordsMastered: number, // 新掌握单词数
      accuracy: number,     // 正确率
      points: number        // 获得积分
    },
    achievements: [{        // 解锁成就
      id: string,
      name: string,
      description: string,
      points: number
    }],
    statistics: {           // 更新后统计
      totalWords: number,
      masteredWords: number,
      studyDays: number,
      currentLevel: number
    },
    recommendations: [{     // 学习建议
      type: string,
      message: string,
      action?: string
    }]
  }
}
```

#### 3.5.3 获取学习历史

```javascript
GET /api/study/history
Authorization: Bearer {token}
Query Parameters:
- type?: string           // 会话类型筛选
- bookId?: number        // 书籍筛选
- startDate?: string     // 开始日期
- endDate?: string       // 结束日期
- page?: number          // 页码
- limit?: number         // 每页数量

Response:
{
  success: true,
  data: {
    sessions: [{
      id: string,
      type: string,
      bookTitle?: string,
      startTime: Date,
      studyTime: number,
      wordsStudied: number,
      points: number,
      accuracy: number
    }],
    statistics: {           // 历史统计
      totalSessions: number,
      totalTime: number,
      averageTime: number,
      averageAccuracy: number,
      bestStreak: number,   // 最佳连续天数
      currentStreak: number // 当前连续天数
    },
    charts: {               // 图表数据
      dailyTime: [{         // 每日学习时长
        date: string,
        time: number
      }],
      weeklyProgress: [{    // 周进度
        week: string,
        words: number,
        accuracy: number
      }]
    },
    pagination: PaginationInfo
  }
}
```

## 4. 性能优化方案

### 4.1 缓存策略设计

#### 4.1.1 Redis缓存层次

```javascript
// 缓存键设计规范
const CACHE_KEYS = {
  // 用户相关缓存 (24小时)
  USER_INFO: 'user:{openid}',
  USER_STATS: 'user:{openid}:stats',
  USER_PROGRESS: 'user:{openid}:progress',
  USER_WORDS: 'user:{openid}:words',

  // 内容缓存 (12小时)
  BOOK_INFO: 'book:{bookId}',
  CHAPTER_INFO: 'chapter:{chapterId}',
  BOOK_CHAPTERS: 'book:{bookId}:chapters',
  
  // 热点数据缓存 (6小时)
  HOME_DATA: 'home:data',
  HOT_BOOKS: 'hot:books:{category}',
  HOT_WORDS: 'hot:words',
  DAILY_PLAN: 'daily:plan:{date}',
  
  // 搜索缓存 (30分钟)
  SEARCH_RESULT: 'search:{hash}',
  
  // 统计缓存 (2小时)
  BOOK_STATS: 'stats:book:{bookId}',
  GLOBAL_STATS: 'stats:global'
};

// 缓存更新策略
const CACHE_STRATEGY = {
  // 写入时更新
  WRITE_THROUGH: ['USER_INFO', 'USER_PROGRESS'],
  
  // 延迟写入
  WRITE_BEHIND: ['USER_STATS', 'BOOK_STATS'],
  
  // 失效更新
  CACHE_ASIDE: ['HOME_DATA', 'SEARCH_RESULT'],
  
  // 定时刷新
  SCHEDULED_REFRESH: ['HOT_BOOKS', 'HOT_WORDS', 'GLOBAL_STATS']
};
```

#### 4.1.2 前端本地缓存

```javascript
// Storage缓存 (持久化)
const STORAGE_KEYS = {
  USER_INFO: 'userInfo',           // 用户基本信息
  STUDY_PREFERENCES: 'studyPrefs', // 学习偏好
  RECENT_BOOKS: 'recentBooks',     // 最近学习书籍
  OFFLINE_WORDS: 'offlineWords',   // 离线单词数据
  CACHE_TIMESTAMP: 'cacheTime'     // 缓存时间戳
};

// Memory缓存 (会话级)
const MEMORY_CACHE = {
  currentSession: null,            // 当前学习会话
  batchQueue: [],                  // 批量操作队列
  wordStates: new Map(),           // 单词状态变更
  pendingActions: [],              // 待同步操作
  homeData: null,                  // 首页数据
  bookCache: new Map()             // 书籍缓存
};

// 缓存过期策略
const CACHE_EXPIRY = {
  USER_INFO: 24 * 60 * 60 * 1000,      // 24小时
  HOME_DATA: 30 * 60 * 1000,           // 30分钟
  BOOK_INFO: 60 * 60 * 1000,           // 1小时
  WORD_STATES: 5 * 60 * 1000           // 5分钟
};
```

### 4.2 批量操作优化

#### 4.2.1 前端批量队列设计

```javascript
class BatchOperationQueue {
  constructor(options = {}) {
    this.queue = [];
    this.timer = null;
    this.interval = options.interval || 3000;  // 3秒批量提交
    this.maxSize = options.maxSize || 100;     // 最大队列长度
    this.maxRetries = options.maxRetries || 3; // 最大重试次数
    this.retryDelay = options.retryDelay || 1000; // 重试延迟
  }

  // 添加操作到队列
  addOperation(operation) {
    this.queue.push({
      ...operation,
      timestamp: Date.now(),
      retries: 0
    });

    // 队列满了立即提交
    if (this.queue.length >= this.maxSize) {
      this.flush();
    } else {
      this.scheduleFlush();
    }
  }

  // 调度提交
  scheduleFlush() {
    if (this.timer) clearTimeout(this.timer);
    this.timer = setTimeout(() => this.flush(), this.interval);
  }

  // 批量提交
  async flush() {
    if (this.queue.length === 0) return;

    const operations = [...this.queue];
    this.queue = [];

    try {
      await this.submitBatch(operations);
    } catch (error) {
      // 失败的操作重新入队重试
      const retryOps = operations
        .filter(op => op.retries < this.maxRetries)
        .map(op => ({ ...op, retries: op.retries + 1 }));
      
      this.queue.unshift(...retryOps);
      
      // 延迟重试
      setTimeout(() => this.scheduleFlush(), this.retryDelay);
    }
  }

  // 提交批量操作
  async submitBatch(operations) {
    const response = await wx.cloud.callFunction({
      name: 'api',
      data: {
        action: 'vocabulary/batch-update',
        sessionId: this.getCurrentSessionId(),
        updates: operations
      }
    });

    if (!response.result.success) {
      throw new Error(response.result.error?.message || '批量更新失败');
    }

    return response.result.data;
  }
}
```

#### 4.2.2 后端批量处理优化

```javascript
// 批量更新单词学习记录
async function batchUpdateWordRecords(openid, updates) {
  const db = cloud.database();
  const batch = db.startTransaction();

  try {
    // 分组处理不同类型的更新
    const groupedUpdates = groupUpdatesByType(updates);
    
    // 批量查询现有记录
    const wordIds = updates.map(u => u.wordId);
    const existingRecords = await db.collection('word_learning_records')
      .where({
        openid: openid,
        wordId: db.command.in(wordIds)
      })
      .get();

    const existingMap = new Map(
      existingRecords.data.map(r => [r.wordId, r])
    );

    // 批量处理更新
    const bulkOps = [];
    let totalPoints = 0;
    let newMastered = 0;

    for (const update of updates) {
      const existing = existingMap.get(update.wordId);
      const operation = await processWordUpdate(existing, update);
      
      bulkOps.push(operation);
      totalPoints += operation.points || 0;
      if (operation.newlyMastered) newMastered++;
    }

    // 执行批量更新
    await executeBulkOperations(batch, bulkOps);
    
    // 更新用户统计
    await updateUserStatistics(batch, openid, {
      totalPoints,
      newMastered
    });

    // 提交事务
    await batch.commit();

    return {
      updated: bulkOps.length,
      points: totalPoints,
      newMastered
    };

  } catch (error) {
    await batch.rollback();
    throw error;
  }
}

// 分组更新操作
function groupUpdatesByType(updates) {
  return updates.reduce((groups, update) => {
    const type = update.action;
    if (!groups[type]) groups[type] = [];
    groups[type].push(update);
    return groups;
  }, {});
}
```

### 4.3 数据库查询优化

#### 4.3.1 聚合查询优化

```javascript
// 首页数据聚合查询
async function getHomeData(openid) {
  const db = cloud.database();
  const $ = db.command.aggregate;

  // 使用聚合管道优化复杂查询
  const pipeline = [
    // 查询用户最近学习的书籍
    {
      $lookup: {
        from: 'user_progress',
        let: { userId: openid },
        pipeline: [
          { $match: { $expr: { $eq: ['$openid', '$$userId'] } } },
          { $sort: { lastStudyAt: -1 } },
          { $limit: 5 },
          {
            $lookup: {
              from: 'books',
              localField: 'bookId',
              foreignField: 'id',
              as: 'book'
            }
          },
          { $unwind: '$book' }
        ],
        as: 'recentBooks'
      }
    },
    
    // 查询推荐书籍
    {
      $lookup: {
        from: 'books',
        pipeline: [
          { $match: { isActive: true } },
          { $sort: { popularity: -1 } },
          { $limit: 10 }
        ],
        as: 'recommendBooks'
      }
    },
    
    // 查询用户统计
    {
      $lookup: {
        from: 'word_learning_records',
        let: { userId: openid },
        pipeline: [
          { $match: { $expr: { $eq: ['$openid', '$$userId'] } } },
          {
            $group: {
              _id: '$status',
              count: { $sum: 1 }
            }
          }
        ],
        as: 'wordStats'
      }
    }
  ];

  const result = await db.collection('users')
    .where({ openid })
    .aggregate()
    .addFields(pipeline)
    .end();

  return result.list[0];
}
```

#### 4.3.2 分页查询优化

```javascript
// 优化的分页查询 (避免skip性能问题)
async function getPaginatedBooks(query, page = 1, limit = 20) {
  const db = cloud.database();
  
  // 使用游标分页替代skip
  if (page === 1) {
    // 第一页直接查询
    return await db.collection('books')
      .where(query)
      .orderBy('id', 'desc')
      .limit(limit)
      .get();
  } else {
    // 后续页使用游标
    const lastId = getLastIdFromPreviousPage(page, limit);
    return await db.collection('books')
      .where({
        ...query,
        id: db.command.lt(lastId)
      })
      .orderBy('id', 'desc')
      .limit(limit)
      .get();
  }
}

// 复杂搜索查询优化
async function searchBooks(keyword, filters, pagination) {
  const db = cloud.database();
  const $ = db.command;
  
  // 构建查询条件
  const whereCondition = {
    isActive: true,
    ...buildFiltersCondition(filters)
  };

  // 全文搜索条件
  if (keyword) {
    whereCondition.$or = [
      { title: new RegExp(keyword, 'i') },
      { author: new RegExp(keyword, 'i') },
      { tags: $.in([keyword]) }
    ];
  }

  // 执行查询
  const [books, total] = await Promise.all([
    db.collection('books')
      .where(whereCondition)
      .orderBy('popularity', 'desc')
      .skip((pagination.page - 1) * pagination.limit)
      .limit(pagination.limit)
      .get(),
    
    db.collection('books')
      .where(whereCondition)
      .count()
  ]);

  return {
    books: books.data,
    total: total.total,
    hasMore: pagination.page * pagination.limit < total.total
  };
}
```

### 4.4 前端性能优化

#### 4.4.1 数据预加载策略

```javascript
class DataPreloader {
  constructor() {
    this.preloadQueue = [];
    this.preloadCache = new Map();
  }

  // 预加载关键数据
  async preloadCriticalData(openid) {
    const preloadTasks = [
      this.preloadUserData(openid),
      this.preloadHomeData(),
      this.preloadRecentBooks(openid),
      this.preloadTodayWords(openid)
    ];

    // 并行预加载
    const results = await Promise.allSettled(preloadTasks);
    
    // 处理预加载结果
    results.forEach((result, index) => {
      if (result.status === 'rejected') {
        console.warn(`预加载任务 ${index} 失败:`, result.reason);
      }
    });
  }

  // 智能预加载 (基于用户行为)
  async smartPreload(userBehavior) {
    const predictions = this.predictNextActions(userBehavior);
    
    for (const prediction of predictions) {
      if (prediction.probability > 0.7) {  // 高概率预加载
        this.schedulePreload(prediction.resource, prediction.priority);
      }
    }
  }

  // 预测用户下一步操作
  predictNextActions(behavior) {
    // 基于历史行为预测
    // 例如：如果用户经常在看完书籍详情后进入第一章
    return [
      {
        resource: 'chapter',
        probability: 0.8,
        priority: 'high'
      }
    ];
  }
}
```

#### 4.4.2 组件级缓存优化

```javascript
// 单词组件缓存
Component({
  lifetimes: {
    created() {
      this.wordCache = new Map();
      this.renderCache = new Map();
    }
  },

  methods: {
    // 渲染优化 - 避免重复渲染
    updateWordList(words) {
      const newWords = words.filter(word => {
        const cached = this.wordCache.get(word.id);
        if (!cached || cached.updatedAt < word.updatedAt) {
          this.wordCache.set(word.id, word);
          return true;
        }
        return false;
      });

      if (newWords.length > 0) {
        this.setData({
          words: this.mergeWordUpdates(this.data.words, newWords)
        });
      }
    },

    // 增量更新
    mergeWordUpdates(currentWords, updates) {
      const updateMap = new Map(updates.map(w => [w.id, w]));
      
      return currentWords.map(word => 
        updateMap.has(word.id) ? updateMap.get(word.id) : word
      );
    },

    // 虚拟滚动优化
    onVirtualScroll(e) {
      const { scrollTop } = e.detail;
      const itemHeight = 80; // 单词项高度
      const containerHeight = 600; // 容器高度
      
      const startIndex = Math.floor(scrollTop / itemHeight);
      const endIndex = Math.min(
        startIndex + Math.ceil(containerHeight / itemHeight) + 2,
        this.data.allWords.length
      );
      
      const visibleWords = this.data.allWords.slice(startIndex, endIndex);
      
      this.setData({
        visibleWords,
        scrollOffset: startIndex * itemHeight
      });
    }
  }
});
```

## 5. 前端交互优化方案

### 5.1 状态管理架构

```javascript
// 全局状态管理器
class GlobalStateManager {
  constructor() {
    this.state = {
      user: null,
      currentBook: null,
      studySession: null,
      wordStates: new Map(),
      cache: new Map(),
      settings: {}
    };
    
    this.listeners = new Map();
    this.batchQueue = new BatchOperationQueue();
  }

  // 状态更新
  setState(path, value) {
    this.updateState(this.state, path.split('.'), value);
    this.notifyListeners(path, value);
  }

  // 监听状态变化
  subscribe(path, callback) {
    if (!this.listeners.has(path)) {
      this.listeners.set(path, []);
    }
    this.listeners.get(path).push(callback);
  }

  // 批量状态更新
  batchUpdate(updates) {
    updates.forEach(({ path, value }) => {
      this.updateState(this.state, path.split('.'), value);
    });
    
    // 批量通知
    updates.forEach(({ path, value }) => {
      this.notifyListeners(path, value);
    });
  }
}
```

### 5.2 数据同步策略

```javascript
// 数据同步管理器
class DataSyncManager {
  constructor(stateManager) {
    this.stateManager = stateManager;
    this.syncQueue = [];
    this.isOnline = true;
    this.retryAttempts = 0;
    this.maxRetries = 3;
  }

  // 网络状态监听
  initNetworkListener() {
    wx.onNetworkStatusChange((res) => {
      this.isOnline = res.isConnected;
      
      if (this.isOnline && this.syncQueue.length > 0) {
        this.processSyncQueue();
      }
    });
  }

  // 添加同步任务
  addSyncTask(task) {
    if (this.isOnline) {
      this.executeSync(task);
    } else {
      this.syncQueue.push(task);
      this.saveOfflineData(task);
    }
  }

  // 处理同步队列
  async processSyncQueue() {
    while (this.syncQueue.length > 0 && this.isOnline) {
      const task = this.syncQueue.shift();
      try {
        await this.executeSync(task);
        this.retryAttempts = 0;
      } catch (error) {
        this.handleSyncError(task, error);
      }
    }
  }

  // 执行同步
  async executeSync(task) {
    const response = await wx.cloud.callFunction({
      name: 'api',
      data: task
    });

    if (response.result.success) {
      this.handleSyncSuccess(task, response.result.data);
    } else {
      throw new Error(response.result.error?.message);
    }
  }

  // 冲突解决
  resolveConflict(local, remote, strategy = 'remote-wins') {
    switch (strategy) {
      case 'remote-wins':
        return remote;
      case 'local-wins':
        return local;
      case 'merge':
        return this.mergeData(local, remote);
      case 'timestamp':
        return local.updatedAt > remote.updatedAt ? local : remote;
      default:
        return remote;
    }
  }
}
```

### 5.3 用户体验优化

```javascript
// 加载状态管理
class LoadingStateManager {
  constructor() {
    this.loadingStates = new Map();
    this.globalLoading = false;
  }

  // 显示加载状态
  showLoading(key, options = {}) {
    this.loadingStates.set(key, {
      startTime: Date.now(),
      message: options.message || '加载中...',
      timeout: options.timeout || 10000
    });

    if (options.global) {
      this.globalLoading = true;
      wx.showLoading({ title: options.message });
    }

    // 超时处理
    setTimeout(() => {
      if (this.loadingStates.has(key)) {
        this.hideLoading(key);
        this.handleTimeout(key);
      }
    }, options.timeout || 10000);
  }

  // 隐藏加载状态
  hideLoading(key) {
    this.loadingStates.delete(key);
    
    if (this.globalLoading && this.loadingStates.size === 0) {
      this.globalLoading = false;
      wx.hideLoading();
    }
  }

  // 智能加载提示
  smartLoading(promise, options = {}) {
    const key = options.key || Date.now().toString();
    
    // 延迟显示加载提示 (避免闪烁)
    const showTimeout = setTimeout(() => {
      this.showLoading(key, options);
    }, options.delay || 200);

    return promise.finally(() => {
      clearTimeout(showTimeout);
      this.hideLoading(key);
    });
  }
}

// 错误处理管理器
class ErrorManager {
  constructor() {
    this.errorHandlers = new Map();
    this.globalHandler = null;
  }

  // 注册错误处理器
  registerHandler(type, handler) {
    this.errorHandlers.set(type, handler);
  }

  // 处理错误
  handleError(error, context = {}) {
    const errorType = this.getErrorType(error);
    const handler = this.errorHandlers.get(errorType) || this.globalHandler;

    if (handler) {
      handler(error, context);
    } else {
      this.defaultErrorHandler(error, context);
    }

    // 错误上报
    this.reportError(error, context);
  }

  // 默认错误处理
  defaultErrorHandler(error, context) {
    const message = this.getUserFriendlyMessage(error);
    
    wx.showToast({
      title: message,
      icon: 'none',
      duration: 2000
    });
  }

  // 获取用户友好的错误信息
  getUserFriendlyMessage(error) {
    const errorMessages = {
      'NETWORK_ERROR': '网络连接异常，请检查网络设置',
      'AUTH_ERROR': '登录已过期，请重新登录',
      'PERMISSION_ERROR': '权限不足，请联系管理员',
      'DATA_ERROR': '数据异常，请稍后重试',
      'TIMEOUT_ERROR': '请求超时，请检查网络连接'
    };

    return errorMessages[error.code] || '操作失败，请稍后重试';
  }
}
```

这个设计方案涵盖了从系统架构到具体实现的完整技术方案，为英语学习小程序的后端接口开发提供了详细的指导。接下来我将创建项目管理TODO文档。

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"id": "1", "content": "\u521b\u5efa\u7cfb\u7edf\u8bbe\u8ba1\u65b9\u6848\u6587\u6863 (design-specification.md)", "status": "completed", "priority": "high"}, {"id": "2", "content": "\u521b\u5efa\u9879\u76ee\u7ba1\u7406TODO\u6587\u6863 (project-todo.md)", "status": "in_progress", "priority": "high"}]