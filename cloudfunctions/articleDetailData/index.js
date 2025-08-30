// 云函数入口文件
const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV }) // 使用当前云环境

const db = cloud.database()

exports.main = async (event, context) => {
  const { type, chapterId, bookId, currentTime, completed } = event
  const { OPENID } = cloud.getWXContext()
  const user_id = OPENID

  console.log('📖 [DEBUG] articleDetailData云函数开始执行:', { type, chapterId, bookId, user_id, currentTime, completed })

  try {
    switch (type) {
      case 'getChapterDetail':
        return await getChapterDetail(chapterId, user_id)
      case 'getChapterVocabularies':
        return await getChapterVocabularies(chapterId, user_id)
      case 'saveChapterProgress':
        return await saveChapterProgress(user_id, bookId, chapterId, currentTime, completed)
      default:
        console.log('❌ [DEBUG] 未知操作类型:', type)
        return {
          code: -1,
          message: '未知操作类型: ' + type
        }
    }
  } catch (err) {
    console.error('❌ [DEBUG] articleDetailData云函数错误:', err)
    return {
      code: -1,
      message: err.message,
      data: null
    }
  }
}

// 获取章节详情
async function getChapterDetail(chapterId, user_id) {
  console.log('🔄 [DEBUG] 开始获取章节详情:', { chapterId, user_id })

  // 参数验证
  if (!chapterId) {
    console.log('❌ [DEBUG] 参数验证失败: 缺少章节ID')
    return {
      code: -1,
      message: '缺少章节ID参数'
    }
  }

  try {
    // 1. 获取章节基本信息
    console.log('📤 [DEBUG] 查询章节基本信息:', chapterId)
    const chapterResult = await db.collection('chapters').doc(chapterId).get()

    if (!chapterResult.data) {
      console.log('❌ [DEBUG] 章节不存在:', chapterId)
      return {
        code: -1,
        message: '章节不存在'
      }
    }

    if (!chapterResult.data.is_active) {
      console.log('❌ [DEBUG] 章节已下架:', chapterId)
      return {
        code: -1,
        message: '章节已下架'
      }
    }

    const chapter = chapterResult.data
    console.log('✅ [DEBUG] 获取到章节信息:', chapter)

    // 2. 获取书籍信息
    console.log('📤 [DEBUG] 查询书籍信息:', chapter.book_id)
    const bookResult = await db.collection('books').doc(chapter.book_id).get()

    if (!bookResult.data) {
      console.log('❌ [DEBUG] 所属书籍不存在:', chapter.book_id)
      return {
        code: -1,
        message: '所属书籍不存在'
      }
    }

    const book = bookResult.data
    console.log('✅ [DEBUG] 书籍信息获取成功:', { title: book.title })

    // 3. 获取用户学习进度（参考homeData写法）
    let userProgress = null
    if (user_id) {
      const progressId = `${user_id}_${chapter.book_id}`
      console.log('📤 [DEBUG] 查询用户学习进度:', progressId)

      await db.collection('user_progress').doc(progressId).get().then(res => {
        if (res.data) {
          userProgress = res.data
          console.log('📥 [DEBUG] 用户进度查询成功:', {
            current_chapter: userProgress.current_chapter,
            completed_count: userProgress.chapters_completed.length
          })
        } else {
          console.log('📥 [DEBUG] 用户进度为空，使用默认值')
        }
      }).catch(err => {
        console.log('📥 [DEBUG] 用户学习进度不存在，使用默认值:', err.message)
      })
    } else {
      console.log('📥 [DEBUG] 用户未登录，跳过进度查询')
    }

    // 4. 构建返回数据，使用数据库原字段
    const result = {
      // 章节信息
      ...chapter,
      // 书籍标题用于页面显示
      book_title: book.title,
      // 用户相关状态
      is_completed: userProgress && userProgress.chapters_completed.includes(chapter.chapter_number),
      is_current: userProgress && userProgress.current_chapter === chapter.chapter_number
    }

    console.log('✅ [DEBUG] 章节详情数据处理完成')

    return {
      code: 0,
      data: result
    }

  } catch (error) {
    console.error('❌ [DEBUG] 获取章节详情失败:', error)
    return {
      code: -1,
      message: '获取章节详情失败: ' + error.message
    }
  }
}

// 获取章节单词
async function getChapterVocabularies(chapterId, user_id) {
  console.log('🔄 [DEBUG] 开始获取章节单词:', { chapterId, user_id })

  if (!chapterId) {
    console.log('❌ [DEBUG] 参数验证失败: 缺少章节ID')
    return {
      code: -1,
      message: '缺少章节ID参数'
    }
  }

  try {
    // 1. 获取章节信息
    console.log('📤 [DEBUG] 查询章节信息:', chapterId)
    const chapterResult = await db.collection('chapters').doc(chapterId).get()

    if (!chapterResult.data) {
      console.log('❌ [DEBUG] 章节不存在:', chapterId)
      return {
        code: -1,
        message: '章节不存在'
      }
    }

    const chapter = chapterResult.data

    // 2. 查询章节相关单词（使用mock数据）
    console.log('📤 [DEBUG] 获取mock单词数据')

    // Mock单词数据，模拟数据库结构
    const mockVocabularies = [
      {
        _id: 'word_001',
        word: 'welcome',
        phonetic: '/ˈwelkəm/',
        translations: [
          { type: 'v.', meaning: '欢迎', example: 'Welcome to our school.' },
          { type: 'n.', meaning: '欢迎', example: 'A warm welcome awaited us.' }
        ],
        difficulty: 'easy',
        frequency: 'high'
      },
      {
        _id: 'word_002',
        word: 'practice',
        phonetic: '/ˈpræktɪs/',
        translations: [
          { type: 'n.', meaning: '练习', example: 'Practice makes perfect.' },
          { type: 'v.', meaning: '练习', example: 'I practice piano every day.' }
        ],
        difficulty: 'easy',
        frequency: 'high'
      },
      {
        _id: 'word_003',
        word: 'listening',
        phonetic: '/ˈlɪsnɪŋ/',
        translations: [
          { type: 'n.', meaning: '听力', example: 'Listening is an important skill.' }
        ],
        difficulty: 'medium',
        frequency: 'high'
      },
      {
        _id: 'word_004',
        word: 'pronunciation',
        phonetic: '/prəˌnʌnsiˈeɪʃn/',
        translations: [
          { type: 'n.', meaning: '发音', example: 'Good pronunciation is essential.' }
        ],
        difficulty: 'medium',
        frequency: 'medium'
      },
      {
        _id: 'word_005',
        word: 'improve',
        phonetic: '/ɪmˈpruːv/',
        translations: [
          { type: 'v.', meaning: '改善', example: 'We need to improve our English.' }
        ],
        difficulty: 'easy',
        frequency: 'high'
      },
      {
        _id: 'word_006',
        word: 'sentence',
        phonetic: '/ˈsentəns/',
        translations: [
          { type: 'n.', meaning: '句子', example: 'Read this sentence carefully.' }
        ],
        difficulty: 'easy',
        frequency: 'high'
      },
      {
        _id: 'word_007',
        word: 'progress',
        phonetic: '/ˈprɑːɡres/',
        translations: [
          { type: 'n.', meaning: '进步', example: 'You are making good progress.' },
          { type: 'v.', meaning: '进步', example: 'Students progress at different rates.' }
        ],
        difficulty: 'medium',
        frequency: 'high'
      },
      {
        _id: 'word_008',
        word: 'platform',
        phonetic: '/ˈplætfɔːrm/',
        translations: [
          { type: 'n.', meaning: '平台', example: 'This is a learning platform.' }
        ],
        difficulty: 'medium',
        frequency: 'medium'
      }
    ]

    console.log('📥 [DEBUG] Mock单词数据加载完成:', { count: mockVocabularies.length })

    // 3. 获取用户单词学习记录（mock数据简化处理）
    let userWordRecords = []
    if (user_id && mockVocabularies.length > 0) {
      const wordIds = mockVocabularies.map(word => word._id)
      console.log('📤 [DEBUG] 查询用户单词学习记录:', wordIds.length)

      // Mock用户单词学习记录
      userWordRecords = [
        { word_id: 'word_001', level: 3, is_mastered: false, last_review_at: new Date() },
        { word_id: 'word_002', level: 5, is_mastered: false, last_review_at: new Date() },
        { word_id: 'word_003', level: 1, is_mastered: false, last_review_at: new Date() }
      ]

      console.log('📥 [DEBUG] Mock用户单词记录:', { count: userWordRecords.length })
    }

    // 4. 合并单词数据和用户学习状态
    const vocabularies = mockVocabularies.map(word => {
      const userRecord = userWordRecords.find(record => record.word_id === word._id)

      return {
        ...word,
        // 用户学习状态
        level: userRecord ? userRecord.level : 0,
        is_mastered: userRecord ? userRecord.level >= 7 : false,
        last_review_at: userRecord ? userRecord.last_review_at : null,
        // 添加默认收藏状态
        isFavorited: false
      }
    })

    console.log('✅ [DEBUG] 章节单词数据处理完成')

    return {
      code: 0,
      data: {
        chapter_title: chapter.title,
        vocabularies: vocabularies
      }
    }

  } catch (error) {
    console.error('❌ [DEBUG] 获取章节单词失败:', error)
    return {
      code: -1,
      message: '获取章节单词失败: ' + error.message
    }
  }
}


// 保存章节学习进度
async function saveChapterProgress(user_id, bookId, chapterId, currentTime, completed) {
  console.log('🔄 [DEBUG] 开始保存章节进度:', { user_id, bookId, chapterId, currentTime, completed })

  if (!user_id || !bookId || !chapterId) {
    console.log('❌ [DEBUG] 参数验证失败:', { user_id, bookId, chapterId })
    return {
      code: -1,
      message: '参数不完整'
    }
  }

  try {
    const progressId = `${user_id}_${bookId}`
    const now = new Date()

    // 获取现有进度记录
    let userProgress = null
    await db.collection('user_progress').doc(progressId).get().then(res => {
      if (res.data) {
        userProgress = res.data
      }
    }).catch(err => {
      console.log('📥 [DEBUG] 用户进度记录不存在，将创建新记录')
    })

    if (userProgress) {
      // 如果章节进度不存在或未完成，则更新章节进度
      if (userProgress.chapter_progress && userProgress.chapter_progress[chapterId] &&
        userProgress.chapter_progress[chapterId].completed == true) {
        console.log('✅ [DEBUG] 章节进度已存在且已完成, chapterId:', chapterId)
      } else {
        // 更新现有记录
        const chapterProgress = userProgress.chapter_progress || {}
        chapterProgress[chapterId] = {
          time: currentTime || 0,
          completed: completed || false
        }

        await db.collection('user_progress').doc(progressId).update({
          data: {
            chapter_progress: chapterProgress,
            updated_at: now
          }
        })

        console.log('✅ [DEBUG] 章节进度更新成功')
      }
    } else {
      // 创建新记录
      const chapterProgress = {}
      chapterProgress[chapterId] = {
        time: currentTime || 0,
        completed: completed || false
      }

      await db.collection('user_progress').add({
        data: {
          _id: progressId,
          user_id: user_id,
          book_id: bookId,
          current_chapter: 1,
          chapter_progress: chapterProgress,
          created_at: now,
          updated_at: now
        }
      })

      console.log('✅ [DEBUG] 新的章节进度记录创建成功')
    }

    return {
      code: 0,
      message: '章节进度保存成功'
    }

  } catch (error) {
    console.error('❌ [DEBUG] 保存章节进度失败:', error)
    return {
      code: -1,
      message: '保存章节进度失败: ' + error.message
    }
  }
}

