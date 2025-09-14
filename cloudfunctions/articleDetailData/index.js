// 云函数入口文件
const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV }) // 使用当前云环境

const db = cloud.database()

// 时间戳工具函数
function getNowTimestamp() {
  return Date.now()
}

exports.main = async (event, context) => {
  const { type, chapterId, bookId, currentTime, completed, word, wordId, page, pageSize, subtitleIndex } = event
  const { OPENID } = cloud.getWXContext()
  const user_id = OPENID

  console.log('📖 [DEBUG] articleDetailData云函数开始执行:', { type, chapterId, bookId, user_id, currentTime, completed, word, wordId, page, pageSize, subtitleIndex })

  try {
    switch (type) {
      case 'getChapterDetail':
        return await getChapterDetail(chapterId, user_id)
      case 'getChapterVocabularies':
        return await getChapterVocabularies(chapterId, user_id, page, pageSize)
      case 'saveChapterProgress':
        return await saveChapterProgress(user_id, bookId, chapterId, currentTime, completed)
      case 'getWordDetail':
        return await getWordDetail(word, user_id, bookId, chapterId)
      case 'addWordToCollection':
        return await addWordToCollection(word, user_id, bookId, chapterId)
      case 'removeWordFromCollection':
        return await removeWordFromCollection(wordId, user_id)
      case 'getSubtitleAnalysis':
        return await getSubtitleAnalysis(bookId, chapterId, subtitleIndex)
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

    // 直接返回章节数据，不需要额外查询
    const result = {
      ...chapter
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

// 获取章节单词（从用户真实学习记录）
async function getChapterVocabularies(chapterId, user_id, page = 1, pageSize = 20) {
  console.log('🔄 [DEBUG] 开始获取章节单词:', { chapterId, user_id, page, pageSize })

  // 加强参数验证
  if (!chapterId) {
    console.log('❌ [DEBUG] 参数验证失败: 缺少章节ID')
    return {
      code: -1,
      message: '缺少章节ID参数'
    }
  }

  if (!user_id) {
    console.log('❌ [DEBUG] 参数验证失败: 缺少用户ID')
    return {
      code: -1,
      message: '缺少用户ID参数'
    }
  }

  // 参数处理和验证
  const currentPage = Math.max(1, parseInt(page) || 1)
  const limit = Math.min(50, Math.max(1, parseInt(pageSize) || 20)) // 限制每页最多50条
  const skip = (currentPage - 1) * limit

  console.log('📊 [DEBUG] 分页参数处理:', { currentPage, limit, skip })

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
    console.log('✅ [DEBUG] 获取到章节信息:', chapter.title)

    // 2. 查询用户在该章节的单词记录
    console.log('📤 [DEBUG] 查询用户单词记录准备:', {
      user_id,
      chapterId,
      user_id_type: typeof user_id,
      chapterId_type: typeof chapterId,
      user_id_value: user_id,
      chapterId_value: chapterId
    })

    // 确保参数为字符串类型
    const userIdStr = String(user_id)
    const chapterIdStr = String(chapterId)

    console.log('🔧 [DEBUG] 转换后的查询参数:', {
      userIdStr,
      chapterIdStr,
      userIdStr_type: typeof userIdStr,
      chapterIdStr_type: typeof chapterIdStr
    })

    // 查询时多取1条用于判断是否还有更多数据
    const wordRecordsResult = await db.collection('word_records')
      .where({
        'user_id': userIdStr,
        'source_chapter_id': chapterIdStr
      })
      .orderBy('_id', 'asc') // 确保分页结果的稳定性
      .skip(skip)
      .limit(limit + 1)
      .get()

    console.log('📥 [DEBUG] 查询到单词记录:', wordRecordsResult.data.length)

    // 判断是否有更多数据
    const hasMore = wordRecordsResult.data.length > limit
    const actualRecords = hasMore ? wordRecordsResult.data.slice(0, limit) : wordRecordsResult.data

    console.log('📊 [DEBUG] 分页结果分析:', {
      查询到: wordRecordsResult.data.length,
      实际返回: actualRecords.length,
      hasMore
    })

    // 如果没有单词记录，返回空数组
    if (actualRecords.length === 0) {
      console.log('📝 [DEBUG] 该页无单词记录')
      return {
        code: 0,
        data: {
          vocabularies: [],
          hasMore: false,
          currentPage,
          pageSize: limit
        }
      }
    }

    // 3. 提取word_id并去重
    const wordIds = [...new Set(actualRecords.map(record => record.word_id))]
    console.log('📤 [DEBUG] 需要查询的单词ID数量:', wordIds.length)

    // 4. 分批查询vocabularies（解决in限制）
    const vocabulariesData = await batchQueryVocabularies(wordIds)
    console.log('📥 [DEBUG] 查询到单词详情:', vocabulariesData.length)

    // 5. 创建单词记录映射，便于合并数据
    const recordsMap = new Map()
    actualRecords.forEach(record => {
      recordsMap.set(record.word_id, record)
    })

    // 6. 合并数据，统一标记为收藏状态（直接使用数据库字段）
    const vocabularies = vocabulariesData.map(word => {
      const userRecord = recordsMap.get(word._id)

      return {
        ...word,
        // 用户学习状态
        level: userRecord ? userRecord.level : 0,
        is_mastered: userRecord ? userRecord.level >= 7 : false,
        last_review_at: userRecord ? userRecord.last_review_at : null,
        // 收藏状态 - 来自word_records的都是收藏状态
        is_favorited: true
      }
    })

    console.log('✅ [DEBUG] 章节单词数据处理完成，返回', vocabularies.length, '个单词')

    return {
      code: 0,
      data: {
        vocabularies: vocabularies,
        hasMore: hasMore,
        currentPage: currentPage,
        pageSize: limit,
        totalInPage: vocabularies.length
      }
    }

  } catch (error) {
    console.error('❌ [DEBUG] 获取章节单词失败:', {
      error: error.message,
      stack: error.stack,
      chapterId,
      user_id,
      errorType: error.constructor.name
    })

    // 根据不同错误类型返回更具体的错误信息
    let errorMessage = '获取章节单词失败'
    if (error.message.includes('查询参数')) {
      errorMessage = '查询参数错误，请检查章节ID和用户ID'
    } else if (error.message.includes('网络')) {
      errorMessage = '网络连接失败，请重试'
    } else if (error.message.includes('权限')) {
      errorMessage = '数据库访问权限不足'
    } else {
      errorMessage = '获取章节单词失败: ' + error.message
    }

    return {
      code: -1,
      message: errorMessage
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
    const now = getNowTimestamp()

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

// 获取单词详情（包含用户收藏状态）
async function getWordDetail(word, user_id, bookId, chapterId) {
  console.log('🔄 [DEBUG] 获取单词详情:', { word, user_id, bookId, chapterId })

  if (!word) {
    return {
      code: -1,
      message: '缺少单词参数'
    }
  }

  try {
    // 1. 查询单词基本信息
    const wordResult = await db.collection('vocabularies').where({
      word: word.toLowerCase()
    }).limit(1).get()

    if (!wordResult.data || wordResult.data.length === 0) {
      console.log('❌ [DEBUG] 单词不存在:', word)
      return {
        code: -1,
        message: '单词不存在'
      }
    }

    const wordInfo = wordResult.data[0]

    // 2. 查询用户收藏状态（全局查询，不限章节）
    let isCollected = false
    if (user_id) {
      // 查询用户是否在任何章节收藏过这个单词
      const userWordQuery = await db.collection('word_records').where({
        user_id: user_id,
        word_id: wordInfo._id
      }).limit(1).get()
      
      console.log('📤 [DEBUG] 全局查询用户单词收藏状态:', {
        user_id,
        word_id: wordInfo._id,
        found: userWordQuery.data.length > 0
      })

      if (userWordQuery.data && userWordQuery.data.length > 0) {
        isCollected = true
      }
    }

    // 3. 组装返回数据
    const result = {
      ...wordInfo,
      is_favorited: isCollected
    }

    console.log('✅ [DEBUG] 单词详情获取成功:', { word, isCollected })

    return {
      code: 0,
      data: result
    }

  } catch (error) {
    console.error('❌ [DEBUG] 获取单词详情失败:', error)
    return {
      code: -1,
      message: '获取单词详情失败: ' + error.message
    }
  }
}

// 添加单词到收藏
async function addWordToCollection(word, user_id, bookId, chapterId) {
  console.log('🔄 [DEBUG] 添加单词到收藏:', { word, user_id, bookId, chapterId })

  if (!word || !user_id) {
    return {
      code: -1,
      message: '参数不完整'
    }
  }

  try {
    // 1. 查询单词信息
    const wordResult = await db.collection('vocabularies').where({
      word: word.toLowerCase()
    }).limit(1).get()

    if (!wordResult.data || wordResult.data.length === 0) {
      return {
        code: -1,
        message: '单词不存在'
      }
    }

    const wordInfo = wordResult.data[0]
    const recordId = `${user_id}_${wordInfo._id}`
    const now = getNowTimestamp()

    // 2. 直接创建或更新记录（使用set覆盖）
    await db.collection('word_records').doc(recordId).set({
      data: {
        user_id: user_id,
        word_id: wordInfo._id,
        source_book_id: bookId,
        source_chapter_id: chapterId,

        level: null,
        first_learn_date: null,
        next_review_date: null,
        actual_review_dates: [],
        created_at: now,
        updated_at: now
      }
    })

    console.log('✅ [DEBUG] 单词添加到收藏成功:', word)

    return {
      code: 0,
      message: '已加入单词本'
    }

  } catch (error) {
    console.error('❌ [DEBUG] 添加单词到收藏失败:', error)
    return {
      code: -1,
      message: '添加失败: ' + error.message
    }
  }
}

// 从收藏中移除单词（硬删除）
async function removeWordFromCollection(wordId, user_id) {
  console.log('🔄 [DEBUG] 从收藏移除单词:', { wordId, user_id })

  if (!wordId || !user_id) {
    return {
      code: -1,
      message: '参数不完整'
    }
  }

  try {
    const recordId = `${user_id}_${wordId}`

    // 直接硬删除记录
    await db.collection('word_records').doc(recordId).remove()

    console.log('✅ [DEBUG] 单词从收藏删除成功:', wordId)

    return {
      code: 0,
      message: '已从单词本移除'
    }

  } catch (error) {
    console.error('❌ [DEBUG] 删除单词收藏失败:', error)
    return {
      code: -1,
      message: '删除失败: ' + error.message
    }
  }
}

// 分批查询辅助函数 - 解决微信云数据库in操作限制（最多20个）
async function batchQueryVocabularies(wordIds) {
  console.log('🔄 [DEBUG] 开始分批查询单词详情:', { wordCount: wordIds.length })

  if (wordIds.length === 0) {
    console.log('📝 [DEBUG] 单词ID列表为空，跳过查询')
    return []
  }

  const batchSize = 20 // 微信云数据库 in 操作限制
  const batches = []

  // 将wordIds分成多个批次
  for (let i = 0; i < wordIds.length; i += batchSize) {
    batches.push(wordIds.slice(i, i + batchSize))
  }

  console.log('📦 [DEBUG] 分批查询:', { batchCount: batches.length, batchSize })

  // 并发查询所有批次
  const _ = db.command
  const batchPromises = batches.map((batch, index) => {
    console.log(`📤 [DEBUG] 查询批次 ${index + 1}:`, batch.length, '个单词')
    return db.collection('vocabularies').where({ '_id': _.in(batch) }).get()
  })

  const batchResults = await Promise.all(batchPromises)

  // 合并所有结果
  const vocabularies = batchResults.flatMap(result => result.data)
  console.log('📥 [DEBUG] 分批查询完成:', { totalFound: vocabularies.length })

  return vocabularies
}

// 获取字幕解析信息
async function getSubtitleAnalysis(bookId, chapterId, subtitleIndex) {
  console.log('🔄 [DEBUG] 开始获取字幕解析信息:', { bookId, chapterId, subtitleIndex })

  // 参数验证
  if (!bookId || !chapterId || subtitleIndex === undefined || subtitleIndex === null) {
    console.log('❌ [DEBUG] 参数验证失败:', { bookId, chapterId, subtitleIndex })
    return {
      code: -1,
      message: '缺少必要参数：书籍ID、章节ID或字幕索引'
    }
  }

  try {
    // 构建查询条件
    const query = {
      book_id: bookId,
      chapter_id: chapterId,
      subtitle_index: parseInt(subtitleIndex)
    }

    console.log('📤 [DEBUG] 查询字幕解析信息:', query)

    // 查询字幕解析数据
    const analysisResult = await db.collection('subtitle_analysis')
      .where(query)
      .limit(1)
      .get()

    console.log('📥 [DEBUG] 查询结果:', analysisResult.data.length)

    if (!analysisResult.data || analysisResult.data.length === 0) {
      console.log('❌ [DEBUG] 未找到字幕解析信息:', query)
      return {
        code: -1,
        message: '未找到该字幕的解析信息'
      }
    }

    const analysisData = analysisResult.data[0]
    console.log('✅ [DEBUG] 获取字幕解析信息成功')

    return {
      code: 0,
      data: analysisData
    }

  } catch (error) {
    console.error('❌ [DEBUG] 获取字幕解析信息失败:', error)
    return {
      code: -1,
      message: '获取字幕解析信息失败: ' + error.message
    }
  }
}
