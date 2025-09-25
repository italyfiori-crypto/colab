# 云函数接口文档

## 概述

本文档详细说明了微信小程序中各个云函数的接口规范，包括请求参数、返回格式和使用示例。

## 通用返回格式

所有云函数都遵循统一的返回格式：

```javascript
{
  "code": 0,      // 状态码：0表示成功，-1表示失败
  "message": "",  // 错误信息（失败时）
  "data": {}      // 返回数据（成功时）
}
```

或对于某些接口：

```javascript
{
  "success": true,    // 操作成功状态
  "message": "",      // 消息提示
  "data": {}          // 返回数据
}
```

## 1. homeData 云函数

### 1.1 获取最近学习书籍

**调用方式**：`wx.cloud.callFunction({ name: 'homeData', data: { ... } })`

**请求参数**：
```javascript
{
  "type": "getRecentBooks"
}
```

**返回数据**：
```javascript
{
  "code": 0,
  "data": [
    {
      "_id": "book_id",
      "title": "书名",
      "author": "作者",
      "cover_url": "封面图片URL",
      "progress": 85  // 阅读进度百分比
    }
  ]
}
```

### 1.2 获取分类书籍

**请求参数**：
```javascript
{
  "type": "getCategoryBooks",
  "category": "文学名著"  // 可选：文学名著、商务英语、影视剧本、新闻
}
```

**返回数据**：
```javascript
{
  "code": 0,
  "data": [
    {
      "_id": "book_id",
      "title": "书名",
      "author": "作者",
      "cover_url": "封面图片URL",
      "category": "文学名著",
      "difficulty": "初级",
      "total_chapters": 12
    }
  ]
}
```

### 1.3 搜索书籍

**请求参数**：
```javascript
{
  "type": "searchBooks",
  "keyword": "搜索关键词"
}
```

**返回数据**：
```javascript
{
  "code": 0,
  "data": [
    {
      "_id": "book_id",
      "title": "书名",
      "author": "作者",
      "cover_url": "封面图片URL",
      "category": "文学名著"
    }
  ]
}
```

### 1.4 获取首页数据

**请求参数**：
```javascript
{
  "type": "getHomeData",
  "category": "文学名著"  // 可选，默认为第一个分类
}
```

**返回数据**：
```javascript
{
  "code": 0,
  "data": {
    "recentBooks": [...],      // 最近学习书籍列表
    "categoryBooks": [...],    // 分类书籍列表
    "categories": [            // 分类列表
      {
        "name": "文学名著",
        "active": true
      }
    ]
  }
}
```

### 1.5 添加到最近阅读

**请求参数**：
```javascript
{
  "type": "addToRecent",
  "book_id": "书籍ID"
}
```

**返回数据**：
```javascript
{
  "code": 0,
  "message": "添加到最近阅读成功"
}
```

## 2. wordStudy 云函数

### 2.1 获取学习统计

**调用方式**：`wx.cloud.callFunction({ name: 'wordStudy', data: { ... } })`

**请求参数**：
```javascript
{
  "action": "getStudyStats"
}
```

**返回数据**：
```javascript
{
  "success": true,
  "data": {
    "totalWords": 1250,        // 总词汇数
    "studiedToday": 25,        // 今日已学习数
    "masteredWords": 180,      // 已掌握数
    "newWordsCount": 20,       // 新学单词数（最大20个）
    "reviewWordsCount": 15,    // 今日需复习单词数
    "overdueWordsCount": 5     // 逾期单词数
  }
}
```

### 2.2 获取单词列表

**请求参数**：
```javascript
{
  "action": "getWordList",
  "type": "new",      // 单词类型：new(新词) | review(复习) | overdue(逾期)
  "limit": 50         // 可选，返回数量限制，默认50
}
```

**返回数据**：
```javascript
{
  "success": true,
  "data": [
    {
      "id": "记录ID",
      "word": "单词",
      "phonetic": "音标",
      "translations": [
        {
          "partOfSpeech": "词性",
          "meaning": "释义"
        }
      ],
      "overdue_days": 3  // 逾期天数（仅逾期单词包含此字段）
    }
  ]
}
```

### 2.3 更新单词记录

**请求参数**：
```javascript
{
  "action": "updateWordRecord",
  "word": "单词",
  "actionType": "start"  // 操作类型：start | review | failed | remember | vague | reset
}
```

**actionType 说明**：
- `start`: 开始学习新单词
- `review`: 复习单词成功
- `failed`: 复习单词失败
- `remember`: 逾期单词-还记得（轻度降级或保持）
- `vague`: 逾期单词-模糊（降1级）
- `reset`: 逾期单词-忘记了（重置到第1级）

**返回数据**：
```javascript
{
  "success": true,
  "message": "更新成功"
}
```

## 3. bookDetailData 云函数

### 3.1 获取书籍详情

**调用方式**：`wx.cloud.callFunction({ name: 'bookDetailData', data: { ... } })`

**请求参数**：
```javascript
{
  "bookId": "书籍ID"
}
```

**返回数据**：
```javascript
{
  "code": 0,
  "data": {
    "bookInfo": {
      "_id": "书籍ID",
      "title": "书名",
      "author": "作者",
      "cover_url": "封面URL",
      "description": "描述",
      "category": "分类",
      "difficulty": "难度",
      "total_chapters": 12,
      "progress": 65  // 用户阅读进度百分比
    },
    "chapters": [
      {
        "_id": "章节ID",
        "title": "章节标题",
        "chapter_number": 1,
        "duration": 300,      // 音频时长（秒）
        "status": "completed", // 状态：available | in-progress | completed | locked
        "progress": 100       // 章节进度百分比
      }
    ],
    "filterOptions": [
      {
        "value": "all",
        "label": "全部章节"
      }
    ]
  }
}
```

## 4. articleDetailData 云函数

### 4.1 获取章节详情

**调用方式**：`wx.cloud.callFunction({ name: 'articleDetailData', data: { ... } })`

**请求参数**：
```javascript
{
  "type": "getChapterDetail",
  "chapterId": "章节ID"
}
```

**返回数据**：
```javascript
{
  "code": 0,
  "data": {
    "_id": "章节ID",
    "title": "章节标题",
    "content": "章节内容",
    "audio_url": "音频URL",
    "duration": 300,
    "chapter_number": 1,
    "book_id": "所属书籍ID"
  }
}
```

### 4.2 获取章节单词

**请求参数**：
```javascript
{
  "type": "getChapterVocabularies",
  "chapterId": "章节ID",
  "page": 1,        // 可选，页码，默认1
  "pageSize": 20    // 可选，每页数量，默认20，最大50
}
```

**返回数据**：
```javascript
{
  "code": 0,
  "data": {
    "vocabularies": [
      {
        "_id": "单词ID",
        "word": "单词",
        "phonetic_us": "美式音标",
        "phonetic_uk": "英式音标",
        "translation": [
          {
            "type": "词性",
            "meaning": "释义"
          }
        ],
        "level": 2,              // 用户学习等级
        "is_mastered": false,    // 是否已掌握
        "last_review_at": null,  // 最后复习时间
        "isFavorited": true      // 是否已收藏
      }
    ],
    "hasMore": true,         // 是否还有更多数据
    "currentPage": 1,        // 当前页码
    "pageSize": 20,          // 每页数量
    "totalInPage": 20        // 当前页实际数量
  }
}
```

### 4.3 保存章节学习进度

**请求参数**：
```javascript
{
  "type": "saveChapterProgress",
  "bookId": "书籍ID",
  "chapterId": "章节ID",
  "currentTime": 180,    // 当前播放时间（秒）
  "completed": false     // 是否已完成
}
```

**返回数据**：
```javascript
{
  "code": 0,
  "message": "章节进度保存成功"
}
```

### 4.4 获取单词详情

**请求参数**：
```javascript
{
  "type": "getWordDetail",
  "word": "单词",
  "bookId": "书籍ID",      // 可选
  "chapterId": "章节ID"    // 可选
}
```

**返回数据**：
```javascript
{
  "code": 0,
  "data": {
    "_id": "单词ID",
    "word": "单词",
    "phonetic_us": "美式音标",
    "phonetic_uk": "英式音标",
    "translation": [
      {
        "type": "词性",
        "meaning": "释义"
      }
    ],
    "isCollected": true  // 用户是否已收藏
  }
}
```

### 4.5 添加单词到收藏

**请求参数**：
```javascript
{
  "type": "addWordToCollection",
  "word": "单词",
  "bookId": "书籍ID",      // 可选
  "chapterId": "章节ID"    // 可选
}
```

**返回数据**：
```javascript
{
  "code": 0,
  "message": "已加入单词本"
}
```

### 4.6 从收藏中移除单词

**请求参数**：
```javascript
{
  "type": "removeWordFromCollection",
  "wordId": "单词ID"
}
```

**返回数据**：
```javascript
{
  "code": 0,
  "message": "已从单词本移除"
}
```

### 4.7 获取章节字幕信息

**请求参数**：
```javascript
{
  "type": "getSubtitles",
  "chapterId": "章节ID"
}
```

**返回数据**：
```javascript
{
  "code": 0,
  "data": {
    "subtitles": [
      {
        "index": 1,
        "timestamp": "00:00:00,000 --> 00:00:06,250",
        "english_text": "Alice was beginning to get very tired of sitting by her sister on the bank,",
        "chinese_text": "爱丽丝开始对坐在姐姐身边的河岸上感到非常疲倦，"
      },
      {
        "index": 2,
        "timestamp": "00:00:06,250 --> 00:00:09,099",
        "english_text": "and of having nothing to do:",
        "chinese_text": "也厌倦了无所事事："
      }
    ],
    "totalCount": 50,        // 字幕总条数
    "duration": "00:03:52",  // 总时长
    "chapterInfo": {
      "chapterId": "章节ID",
      "title": "章节标题",
      "book_id": "所属书籍ID"
    }
  }
}
```

## 错误处理

### 常见错误码

- `code: 0` - 操作成功
- `code: -1` - 操作失败（详见 message 字段）
- `success: true` - 操作成功
- `success: false` - 操作失败（详见 message 字段）

### 常见错误信息

- "参数不完整" - 缺少必需的请求参数
- "书籍不存在" - 指定的书籍ID不存在
- "书籍已下架" - 书籍状态为非激活
- "章节不存在" - 指定的章节ID不存在
- "章节已下架" - 章节状态为非激活
- "单词不存在" - 指定的单词不存在
- "字幕文件不存在" - 指定章节的字幕文件不存在
- "字幕文件格式错误" - 字幕文件格式不正确或损坏
- "未知操作类型" - 请求的操作类型不支持

## 用户认证

所有云函数都会自动获取用户的 `OPENID`，无需在请求中传递用户ID。云函数内部通过 `cloud.getWXContext().OPENID` 获取当前用户标识。

## 数据库集合说明

- `books` - 书籍信息
- `chapters` - 章节信息
- `vocabularies` - 单词词典
- `user_word_progress` - 用户单词学习记录
- `user_book_progress` - 用户阅读进度
- `analysis` - 字幕解析信息

## 文件系统数据说明

- **字幕数据**: 存储在文件系统中，路径为 `output/{book_name}/subtitles/{chapter_id}.jsonl`
- **字幕格式**: JSONL格式，每行一个JSON对象，包含index、timestamp、english_text、chinese_text字段
- **数据访问**: 通过`getSubtitles`接口直接读取文件系统中的字幕文件

### user_word_progress 字段说明

```javascript
{
  _id: string,                    // 记录ID (user_id_word_id)
  user_id: string,                // 用户ID
  word_id: string,                // 单词ID
  source_book_id: string,         // 来源书籍ID
  source_chapter_id: string,      // 来源章节ID
  
  // 学习状态
  level: number,                  // 记忆等级 0-7 (0=新词, 1-6=复习阶段, 7=已掌握)
  first_learn_date: string,       // 首次学习日期 (YYYY-MM-DD)
  next_review_date: string,       // 下次复习日期 (YYYY-MM-DD)
  actual_review_dates: string[]   // 实际复习日期列表 (YYYY-MM-DD)
}
```

## 注意事项

1. 所有日期字段都使用 `YYYY-MM-DD` 字符串格式，便于查询和比较
2. 单词查询不区分大小写
3. 分页查询中，`hasMore` 字段指示是否还有更多数据
4. 用户进度数据会自动创建和更新
5. 单词收藏状态与学习记录关联
6. 艾宾浩斯复习算法自动计算下次复习时间
7. `first_learn_date` 仅在首次学习时设置，后续不会更新
8. `actual_review_dates` 记录每次实际复习的日期，用于学习统计
9. **字幕数据**：字幕信息直接从JSONL文件读取，不存储在数据库中，提供更高效的数据访问
10. **字幕解析数据**：`analysis` 表存储AI解析结果，与字幕文件通过章节ID关联
11. 字幕文件路径固定为 `output/{book_name}/subtitles/{chapter_id}.jsonl` 格式