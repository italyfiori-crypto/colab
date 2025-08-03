/**
 * 数据库初始化脚本
 * 定义所有集合的数据结构和初始化数据
 */

const cloud = require("wx-server-sdk");

cloud.init({
  env: cloud.DYNAMIC_CURRENT_ENV,
});

const db = cloud.database();

/**
 * 数据库集合定义
 */
const collections = {
  // 用户集合
  users: {
    name: 'users',
    schema: {
      openid: 'string',           // 微信openid，主键
      nickname: 'string',         // 昵称
      avatar: 'string',           // 头像URL
      level: 'number',            // 用户等级，默认1
      totalPoints: 'number',      // 总积分，默认0
      studyDays: 'number',        // 连续学习天数，默认0
      totalStudyTime: 'number',   // 总学习时长(分钟)，默认0
      preferences: 'object',      // 学习偏好设置
      createdAt: 'date',          // 注册时间
      lastLoginAt: 'date',        // 最后登录时间
      updatedAt: 'date'           // 更新时间
    },
    indexes: [
      { keys: { openid: 1 }, unique: true },
      { keys: { level: -1, totalPoints: -1 } },
      { keys: { createdAt: -1 } }
    ]
  },

  // 书籍集合
  books: {
    name: 'books',
    schema: {
      id: 'number',               // 书籍ID
      title: 'string',            // 书名
      author: 'string',           // 作者
      cover: 'string',            // 封面图URL
      category: 'string',         // 分类: literature/business/script/news
      description: 'string',      // 描述
      difficulty: 'string',       // 难度: easy/medium/hard
      totalChapters: 'number',    // 总章节数
      estimatedTime: 'number',    // 预估学习时长(分钟)
      vocabularyCount: 'number',  // 词汇量
      popularity: 'number',       // 受欢迎程度
      isActive: 'boolean',        // 是否上架
      tags: 'array',              // 标签
      createdAt: 'date',
      updatedAt: 'date'
    },
    indexes: [
      { keys: { id: 1 }, unique: true },
      { keys: { category: 1, isActive: 1 } },
      { keys: { difficulty: 1, category: 1 } },
      { keys: { popularity: -1 } },
      { keys: { createdAt: -1 } }
    ]
  },

  // 章节集合
  chapters: {
    name: 'chapters',
    schema: {
      id: 'number',               // 章节ID
      bookId: 'number',           // 所属书籍ID
      chapterNumber: 'number',    // 章节序号
      title: 'string',            // 章节标题
      content: 'string',          // 章节内容
      vocabularyIds: 'array',     // 关联单词ID列表
      estimatedTime: 'number',    // 预估学习时长(分钟)
      difficulty: 'string',       // 难度等级
      isActive: 'boolean',        // 是否启用
      createdAt: 'date',
      updatedAt: 'date'
    },
    indexes: [
      { keys: { id: 1 }, unique: true },
      { keys: { bookId: 1, chapterNumber: 1 } },
      { keys: { bookId: 1, isActive: 1 } }
    ]
  },

  // 单词集合
  vocabularies: {
    name: 'vocabularies',
    schema: {
      id: 'number',               // 单词ID
      word: 'string',             // 单词
      phonetic: 'string',         // 音标
      translations: 'array',      // 翻译列表 [{partOfSpeech, meaning}]
      difficulty: 'string',       // 难度: easy/medium/hard
      frequency: 'string',        // 使用频率: high/medium/low
      examples: 'array',          // 例句列表
      audioUrl: 'string',         // 发音音频URL
      tags: 'array',              // 标签
      bookIds: 'array',           // 关联的书籍ID列表
      usage: 'number',            // 使用次数
      createdAt: 'date',
      updatedAt: 'date'
    },
    indexes: [
      { keys: { id: 1 }, unique: true },
      { keys: { word: 1 }, unique: true },
      { keys: { difficulty: 1, frequency: 1 } },
      { keys: { bookIds: 1 } },
      { keys: { usage: -1 } }
    ]
  },

  // 用户学习进度集合
  userProgress: {
    name: 'user_progress',
    schema: {
      openid: 'string',           // 用户openid
      bookId: 'number',           // 书籍ID
      currentChapter: 'number',   // 当前章节
      totalChapters: 'number',    // 总章节数
      progress: 'number',         // 进度百分比(0-100)
      studyTime: 'number',        // 累计学习时长(分钟)
      lastStudyAt: 'date',        // 最后学习时间
      status: 'string',           // 学习状态: not_started/studying/completed
      createdAt: 'date',
      updatedAt: 'date'
    },
    indexes: [
      { keys: { openid: 1, bookId: 1 }, unique: true },
      { keys: { openid: 1, lastStudyAt: -1 } },
      { keys: { openid: 1, status: 1 } }
    ]
  },

  // 单词学习记录集合
  wordLearningRecords: {
    name: 'word_learning_records',
    schema: {
      openid: 'string',           // 用户openid
      wordId: 'number',           // 单词ID
      status: 'string',           // 学习状态: new/learning/mastered
      correctCount: 'number',     // 答对次数
      totalCount: 'number',       // 总测试次数
      accuracy: 'number',         // 正确率
      firstStudyAt: 'date',       // 首次学习时间
      lastStudyAt: 'date',        // 最后学习时间
      masteredAt: 'date',         // 掌握时间
      reviewAt: 'date',           // 下次复习时间
      reviewLevel: 'number',      // 复习等级(艾宾浩斯)
      createdAt: 'date',
      updatedAt: 'date'
    },
    indexes: [
      { keys: { openid: 1, wordId: 1 }, unique: true },
      { keys: { openid: 1, status: 1 } },
      { keys: { openid: 1, reviewAt: 1 } },
      { keys: { openid: 1, lastStudyAt: -1 } }
    ]
  },

  // 学习会话记录集合
  studySessions: {
    name: 'study_sessions',
    schema: {
      id: 'string',               // 会话ID
      openid: 'string',           // 用户openid
      bookId: 'number',           // 书籍ID
      chapterId: 'number',        // 章节ID
      startTime: 'date',          // 开始时间
      endTime: 'date',            // 结束时间
      studyTime: 'number',        // 学习时长(秒)
      wordsStudied: 'array',      // 学习的单词ID列表
      actions: 'array',           // 用户操作记录
      points: 'number',           // 获得积分
      createdAt: 'date'
    },
    indexes: [
      { keys: { id: 1 }, unique: true },
      { keys: { openid: 1, createdAt: -1 } },
      { keys: { openid: 1, bookId: 1 } }
    ]
  },

  // 每日学习计划集合
  dailyPlans: {
    name: 'daily_plans',
    schema: {
      date: 'string',             // 日期 YYYY-MM-DD
      dayKey: 'string',           // 天数标识 day1/day2...
      totalWords: 'number',       // 当天总单词数
      words: 'array',             // 单词ID列表
      isActive: 'boolean',        // 是否启用
      createdAt: 'date',
      updatedAt: 'date'
    },
    indexes: [
      { keys: { date: 1 }, unique: true },
      { keys: { dayKey: 1 }, unique: true },
      { keys: { isActive: 1 } }
    ]
  }
};

/**
 * 创建集合和索引
 */
async function createCollections() {
  try {
    for (const collectionConfig of Object.values(collections)) {
      const { name, indexes } = collectionConfig;
      
      try {
        // 创建集合
        await db.createCollection(name);
        console.log(`集合 ${name} 创建成功`);
        
        // 创建索引 (在实际应用中，索引创建需要在云数据库控制台进行)
        console.log(`集合 ${name} 需要创建的索引:`, indexes);
        
      } catch (error) {
        // 集合已存在是正常情况
        if (error.errCode === -2) {
          console.log(`集合 ${name} 已存在`);
        } else {
          console.error(`创建集合 ${name} 失败:`, error);
        }
      }
    }
    
    return {
      success: true,
      message: '数据库初始化完成',
      collections: Object.keys(collections)
    };
    
  } catch (error) {
    console.error('数据库初始化失败:', error);
    return {
      success: false,
      error: error.message || error
    };
  }
}

/**
 * 插入初始数据
 */
async function insertInitialData() {
  try {
    // 插入书籍数据
    const books = [
      {
        id: 1,
        title: '了不起的盖茨比',
        author: 'F.司各特·菲茨杰拉德',
        cover: 'https://images.unsplash.com/photo-1621351183012-e2f9972dd9bf?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80',
        category: 'literature',
        description: '美国梦的经典诠释，爵士时代的浮华与幻灭',
        difficulty: 'medium',
        totalChapters: 9,
        estimatedTime: 480,
        vocabularyCount: 150,
        popularity: 95,
        isActive: true,
        tags: ['经典', '美国文学', '爵士时代'],
        createdAt: new Date(),
        updatedAt: new Date()
      },
      {
        id: 2,
        title: '哈利·波特与魔法石',
        author: 'J.K. 罗琳',
        cover: 'https://images.unsplash.com/photo-1481627834876-b7833e8f5570?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80',
        category: 'literature',
        description: '魔法世界的奇幻冒险，适合英语学习',
        difficulty: 'easy',
        totalChapters: 17,
        estimatedTime: 720,
        vocabularyCount: 200,
        popularity: 98,
        isActive: true,
        tags: ['奇幻', '青少年', '畅销书'],
        createdAt: new Date(),
        updatedAt: new Date()
      },
      {
        id: 3,
        title: '商务英语口语精选',
        author: '李明',
        cover: 'https://images.unsplash.com/photo-1560472354-b33ff0c44a43?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80',
        category: 'business',
        description: '实用商务英语对话，职场必备',
        difficulty: 'medium',
        totalChapters: 12,
        estimatedTime: 360,
        vocabularyCount: 300,
        popularity: 85,
        isActive: true,
        tags: ['商务', '口语', '职场'],
        createdAt: new Date(),
        updatedAt: new Date()
      }
    ];

    // 插入每日学习计划数据
    const dailyPlans = [
      {
        date: '2024-01-01',
        dayKey: 'day1',
        totalWords: 8,
        words: [1, 2, 3, 4, 5, 6, 7, 8],
        isActive: true,
        createdAt: new Date(),
        updatedAt: new Date()
      },
      {
        date: '2024-01-02',
        dayKey: 'day2',
        totalWords: 10,
        words: [9, 10, 11, 12, 13, 14, 15, 16, 17, 18],
        isActive: true,
        createdAt: new Date(),
        updatedAt: new Date()
      },
      {
        date: '2024-01-03',
        dayKey: 'day3',
        totalWords: 12,
        words: [19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30],
        isActive: true,
        createdAt: new Date(),
        updatedAt: new Date()
      }
    ];

    // 批量插入书籍数据
    for (const book of books) {
      await db.collection('books').add({ data: book });
    }

    // 批量插入每日计划数据
    for (const plan of dailyPlans) {
      await db.collection('daily_plans').add({ data: plan });
    }

    console.log('初始数据插入成功');
    return { success: true, message: '初始数据插入完成' };

  } catch (error) {
    console.error('插入初始数据失败:', error);
    return { success: false, error: error.message || error };
  }
}

module.exports = {
  collections,
  createCollections,
  insertInitialData
};