// 单词学习云函数
const cloud = require('wx-server-sdk')

cloud.init({
  env: cloud.DYNAMIC_CURRENT_ENV
})

const db = cloud.database()

// 艾宾浩斯复习间隔 (天数)
const REVIEW_INTERVALS = [1, 2, 4, 7, 15, 30, 60]

// 计算下次复习时间
function calculateNextReviewTime(level, isCorrect = true) {
  let newLevel = level
  
  if (isCorrect) {
    newLevel = Math.min(level + 1, 6)
  } else {
    newLevel = Math.max(level - 1, 0)
  }
  
  const interval = REVIEW_INTERVALS[newLevel]
  const randomFactor = 0.8 + Math.random() * 0.4 // 0.8-1.2
  const actualInterval = Math.round(interval * randomFactor)
  
  const nextReviewTime = new Date()
  nextReviewTime.setDate(nextReviewTime.getDate() + actualInterval)
  
  return {
    level: newLevel,
    next_review_at: nextReviewTime
  }
}

// 计算逾期天数
function calculateOverdueDays(nextReviewAt) {
  const now = new Date()
  const reviewDate = new Date(nextReviewAt)
  const diffTime = now.getTime() - reviewDate.getTime()
  const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24))
  return Math.max(0, diffDays)
}

// 处理逾期单词的等级调整
function handleOverdueWordLevel(originalLevel, action, overdueDays) {
  switch (action) {
    case 'remember': // 还记得
      if (overdueDays <= 2) {
        return originalLevel // 轻度逾期保持等级
      } else {
        return Math.max(1, originalLevel - 1) // 降1级
      }
    case 'vague': // 模糊
      return Math.max(1, originalLevel - 1) // 降1级
    case 'forgot': // 忘记了
      return 1 // 重置为第一级
    default:
      return originalLevel
  }
}

exports.main = async (event, context) => {
  const { action, ...params } = event
  const wxContext = cloud.getWXContext()
  const userId = wxContext.OPENID

  try {
    switch (action) {
      case 'getStudyStats':
        return await getStudyStats(userId)
      case 'getWordList':
        return await getWordList(userId, params)
      case 'updateWordRecord':
        return await updateWordRecord(userId, params)
      default:
        return {
          success: false,
          message: '未知的操作类型'
        }
    }
  } catch (error) {
    console.error('云函数执行错误:', error)
    return {
      success: false,
      message: error.message || '服务器错误'
    }
  }
}

// 获取学习统计数据
async function getStudyStats(userId) {
  const today = new Date()
  const todayStart = new Date(today.getFullYear(), today.getMonth(), today.getDate())
  const todayEnd = new Date(todayStart.getTime() + 24 * 60 * 60 * 1000)

  // 统计总词汇数
  const totalWordsResult = await db.collection('word_records')
    .where({ user_id: userId })
    .count()

  // 统计今日已学习数
  const studiedTodayResult = await db.collection('word_records')
    .where({
      user_id: userId,
      learn_at: db.command.gte(todayStart).and(db.command.lt(todayEnd))
    })
    .count()

  // 统计已掌握数
  const masteredResult = await db.collection('word_records')
    .where({
      user_id: userId,
      level: 7
    })
    .count()

  // 统计新学单词数 (TODO: 从章节单词表中获取未学习的单词)
  const newWordsCount = 10 // 临时写死

  // 统计今日需复习单词数
  const reviewWordsResult = await db.collection('word_records')
    .where({
      user_id: userId,
      level: db.command.gte(1).and(db.command.lt(7)),
      next_review_at: db.command.gte(todayStart).and(db.command.lt(todayEnd))
    })
    .count()

  // 统计逾期单词数
  const overdueWordsResult = await db.collection('word_records')
    .where({
      user_id: userId,
      level: db.command.gte(1).and(db.command.lt(7)),
      next_review_at: db.command.lt(todayStart)
    })
    .count()

  return {
    success: true,
    data: {
      totalWords: totalWordsResult.total,
      studiedToday: studiedTodayResult.total,
      masteredWords: masteredResult.total,
      newWordsCount: newWordsCount,
      reviewWordsCount: reviewWordsResult.total,
      overdueWordsCount: overdueWordsResult.total
    }
  }
}

// 获取指定类型的单词列表
async function getWordList(userId, { type, limit = 50 }) {
  const today = new Date()
  const todayStart = new Date(today.getFullYear(), today.getMonth(), today.getDate())
  
  let query
  
  switch (type) {
    case 'new':
      // 获取level=0的待学习单词
      query = db.collection('word_records')
        .where({
          user_id: userId,
          level: 0
        })
        .limit(limit)
      break

    case 'review':
      query = db.collection('word_records')
        .where({
          user_id: userId,
          level: db.command.gte(1).and(db.command.lt(7)),
          next_review_at: db.command.gte(todayStart).and(db.command.lt(new Date(todayStart.getTime() + 24 * 60 * 60 * 1000)))
        })
        .limit(limit)
      break

    case 'overdue':
      query = db.collection('word_records')
        .where({
          user_id: userId,
          level: db.command.gte(1).and(db.command.lt(7)),
          next_review_at: db.command.lt(todayStart)
        })
        .limit(limit)
      break

    default:
      throw new Error('无效的单词类型')
  }

  const wordsResult = await query.get()
  
  // 获取单词详细信息并计算逾期天数
  const words = await Promise.all(wordsResult.data.map(async record => {
    // 根据word_id从vocabularies表获取单词详情
    const wordDetail = await db.collection('vocabularies')
      .doc(record.word_id)
      .get()

    let wordData = {
      id: record._id,
      word: wordDetail.data.word,
      phonetic: wordDetail.data.phonetic_us || wordDetail.data.phonetic_uk || wordDetail.data.phonetic,
      translations: wordDetail.data.translation.map(t => ({
        partOfSpeech: t.type,
        meaning: t.meaning
      }))
    }

    // 如果是逾期单词，添加逾期天数
    if (type === 'overdue') {
      wordData.overdue_days = calculateOverdueDays(record.next_review_at)
    }

    return wordData
  }))

  return {
    success: true,
    data: words
  }
}

// 更新单词记录
async function updateWordRecord(userId, { wordId, actionType, isCorrect, overdueDays }) {
  const now = new Date()
  
  try {
    // 查找现有记录
    const recordId = `${userId}_${wordId}`
    const existingRecord = await db.collection('word_records').doc(recordId).get()

    if (actionType === 'start_learning') {
      // 开始学习新单词
      if (existingRecord.data.length > 0) {
        // 更新现有记录
        const { level, next_review_at } = calculateNextReviewTime(0, true)
        await db.collection('word_records').doc(recordId).update({
          level: level,
          learn_at: now,
          next_review_at: next_review_at,
          finished_dates: db.command.push(now.toISOString().split('T')[0])
        })
      } else {
        // 创建新记录
        const { level, next_review_at } = calculateNextReviewTime(0, true)
        await db.collection('word_records').add({
          data: {
            _id: recordId,
            user_id: userId,
            word_id: wordId,
            level: level,
            learn_at: now,
            next_review_at: next_review_at,
            finished_dates: [now.toISOString().split('T')[0]]
          }
        })
      }
    } else if (actionType === 'review') {
      // 复习单词
      const record = existingRecord.data[0]
      const { level, next_review_at } = calculateNextReviewTime(record.level, isCorrect)
      
      await db.collection('word_records').doc(recordId).update({
        level: level,
        next_review_at: next_review_at,
        finished_dates: db.command.push(now.toISOString().split('T')[0])
      })
    } else if (actionType === 'handle_overdue') {
      // 处理逾期单词
      const record = existingRecord.data[0]
      const newLevel = handleOverdueWordLevel(record.level, isCorrect, overdueDays)
      const { next_review_at } = calculateNextReviewTime(newLevel - 1, true) // 减1是因为函数内部会加1
      
      await db.collection('word_records').doc(recordId).update({
        level: newLevel,
        next_review_at: next_review_at,
        finished_dates: db.command.push(now.toISOString().split('T')[0])
      })
    }

    return {
      success: true,
      message: '更新成功'
    }
  } catch (error) {
    console.error('更新单词记录失败:', error)
    return {
      success: false,
      message: '更新失败'
    }
  }
}