// 单词学习云函数
const cloud = require('wx-server-sdk')

cloud.init({
  env: cloud.DYNAMIC_CURRENT_ENV
})

const db = cloud.database()

// 艾宾浩斯复习间隔 (天数)
const REVIEW_INTERVALS = [1, 2, 4, 7, 15, 30, 60]


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

  const nextReviewDate = new Date()
  nextReviewDate.setDate(nextReviewDate.getDate() + actualInterval)

  return {
    level: newLevel,
    next_review_date: nextReviewDate.toISOString().split('T')[0] // 直接返回字符串格式
  }
}

// 计算逾期天数
function calculateOverdueDays(nextReviewDate) {
  const todayString = new Date().toISOString().split('T')[0]

  // 如果今天小于等于复习日期，则没有逾期
  if (todayString <= nextReviewDate) {
    return 0
  }

  // 计算天数差
  const todayMs = new Date(todayString).getTime()
  const reviewMs = new Date(nextReviewDate).getTime()
  const diffDays = Math.floor((todayMs - reviewMs) / (1000 * 60 * 60 * 24))
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


// 获取学习统计数据
async function getStudyStats(userId) {
  const todayString = new Date().toISOString().split('T')[0] // YYYY-MM-DD 格式

  // 统计总词汇数
  const totalWordsResult = await db.collection('word_records')
    .where({ user_id: userId })
    .count()

  // 统计今日已学习数
  const studiedTodayResult = await db.collection('word_records')
    .where({
      user_id: userId,
      first_learn_date: todayString
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
  const newWordsResult = await db.collection('word_records')
    .where({
      user_id: userId,
      level: 0
    })
    .count()

  // 统计今日需复习单词数
  const reviewWordsResult = await db.collection('word_records')
    .where({
      user_id: userId,
      level: db.command.gte(1).and(db.command.lt(7)),
      next_review_date: todayString
    })
    .count()

  // 统计逾期单词数
  const overdueWordsResult = await db.collection('word_records')
    .where({
      user_id: userId,
      level: db.command.gte(1).and(db.command.lt(7)),
      next_review_date: db.command.lt(todayString)
    })
    .count()

  return {
    success: true,
    data: {
      totalWords: totalWordsResult.total,
      studiedToday: studiedTodayResult.total,
      masteredWords: masteredResult.total,
      newWordsCount: Math.min(20, newWordsResult.total),
      reviewWordsCount: reviewWordsResult.total,
      overdueWordsCount: overdueWordsResult.total
    }
  }
}

// 获取指定类型的单词列表
async function getWordList(userId, { type, limit = 50 }) {
  const todayString = new Date().toISOString().split('T')[0] // YYYY-MM-DD 格式

  let query

  switch (type) {
    case 'new':
      // 计算今日已学习的新单词数量
      const studiedTodayResult = await db.collection('word_records')
        .where({
          user_id: userId,
          level: db.command.gte(1), // level从0变为1及以上表示已学习
          first_learn_date: todayString
        })
        .count()

      const studiedToday = studiedTodayResult.total
      const maxDailyNew = 20
      const remainingToday = Math.max(0, maxDailyNew - studiedToday)

      console.log(`🔄 [DEBUG] 今日新学单词统计: 已学${studiedToday}个，剩余${remainingToday}个`)

      if (remainingToday === 0) {
        return {
          success: true,
          data: []
        }
      }

      // 获取level=0的待学习单词，使用固定排序
      query = db.collection('word_records')
        .where({
          user_id: userId,
          level: 0
        })
        .orderBy('_id', 'asc') // 固定排序确保每次进入看到相同顺序
        .limit(Math.min(remainingToday, limit))
      break

    case 'review':
      console.log('🔄 [DEBUG] 查询复习单词 - 查询条件:', {
        user_id: userId,
        等级范围: '1-6',
        复习日期: todayString,
        今天日期: todayString,
        limit: limit
      })
      
      query = db.collection('word_records')
        .where({
          user_id: userId,
          level: db.command.gte(1).and(db.command.lt(7)),
          next_review_date: todayString
        })
        .limit(limit)
      break

    case 'overdue':
      query = db.collection('word_records')
        .where({
          user_id: userId,
          level: db.command.gte(1).and(db.command.lt(7)),
          next_review_date: db.command.lt(todayString)
        })
        .limit(limit)
      break

    default:
      throw new Error('无效的单词类型')
  }

  const wordsResult = await query.get()

  console.log("🔄 [DEBUG] 获取单词列表:", {
    查询类型: type,
    查询结果数量: wordsResult.data.length,
    详细数据: wordsResult.data.map(record => ({
      单词ID: record.word_id,
      等级: record.level,
      下次复习日期: record.next_review_date,
      今天: todayString,
      是否匹配: record.next_review_date === todayString
    }))
  })

  if (wordsResult.data.length === 0) {
    console.log("📝 [DEBUG] 没有找到符合条件的单词记录")
    return {
      success: true,
      data: []
    }
  }

  // 收集所有有效的word_id
  const wordIds = wordsResult.data
    .filter(record => record.word_id && typeof record.word_id === 'string')
    .map(record => record.word_id)

  console.log('📋 [DEBUG] 需要查询的word_ids:', wordIds)

  if (wordIds.length === 0) {
    console.warn('⚠️ [WARN] 没有有效的word_id字段')
    return {
      success: true,
      data: []
    }
  }

  // 批量查询vocabularies表
  const vocabulariesResult = await db.collection('vocabularies')
    .where({
      _id: db.command.in(wordIds)
    })
    .get()

  console.log('📚 [DEBUG] 查询到的词汇数量:', vocabulariesResult.data.length)

  // 创建词汇字典，便于快速查找
  const vocabularyMap = new Map()
  vocabulariesResult.data.forEach(vocab => {
    vocabularyMap.set(vocab._id, vocab)
  })

  // 处理单词记录并匹配词汇详情
  const words = wordsResult.data
    .filter(record => record.word_id && vocabularyMap.has(record.word_id))
    .map(record => {
      const vocab = vocabularyMap.get(record.word_id)

      let wordData = {
        id: record._id,
        word: vocab.word,
        phonetic: vocab.phonetic_us || vocab.phonetic_uk || vocab.phonetic,
        translations: vocab.translation.map(t => ({
          partOfSpeech: t.type,
          meaning: t.meaning
        }))
      }

      // 如果是逾期单词，添加逾期天数
      if (type === 'overdue') {
        wordData.overdue_days = calculateOverdueDays(record.next_review_date)
      }

      return wordData
    })

  console.log('📊 [DEBUG] 成功处理单词数量:', words.length, '原始记录数:', wordsResult.data.length)

  return {
    success: true,
    data: words
  }
}

// 更新单词记录
async function updateWordRecord(userId, { word, actionType }) {
  const now = new Date()
  const todayString = now.toISOString().split('T')[0] // YYYY-MM-DD 格式

  console.log('📖 [DEBUG] updateWordRecord云函数开始执行:', { word, actionType })
  try {
    // 查找现有记录
    const recordId = `${userId}_${word}`
    let existingRecord

    try {
      existingRecord = await db.collection('word_records').doc(recordId).get()
    } catch (error) {
      // 记录不存在时，get()会抛出错误
      existingRecord = { data: null }
    }

    if (actionType === 'start') {
      // 开始学习新单词
      if (existingRecord.data) {
        // 更新现有记录
        const { level, next_review_date } = calculateNextReviewTime(0, true)
        await db.collection('word_records').doc(recordId).update({
          data: {
            level: level,
            first_learn_date: todayString,
            next_review_date: next_review_date,
            actual_review_dates: db.command.push(todayString)
          }
        })
      }
    } else if (actionType === 'review') {
      const record = existingRecord.data
      console.log('📖 [DEBUG] 复习单词成功 - 更新前状态:', {
        word,
        当前等级: record.level,
        当前复习日期: record.next_review_date,
        今天: todayString
      })

      const { level, next_review_date } = calculateNextReviewTime(record.level, true)
      console.log('📖 [DEBUG] 复习单词成功 - 计算新状态:', {
        新等级: level,
        新复习日期: next_review_date
      })

      await db.collection('word_records').doc(recordId).update({
        data: {
          level: level,
          next_review_date: next_review_date,
          actual_review_dates: db.command.push(todayString)
        }
      })

      console.log('✅ [DEBUG] 复习单词成功 - 数据库更新完成')

      // 验证数据库更新是否成功
      try {
        const verifyRecord = await db.collection('word_records').doc(recordId).get()
        console.log('🔍 [DEBUG] 验证数据库更新结果:', {
          单词: word,
          更新后等级: verifyRecord.data.level,
          更新后复习日期: verifyRecord.data.next_review_date,
          预期等级: level,
          预期复习日期: next_review_date,
          更新是否成功: verifyRecord.data.level === level && verifyRecord.data.next_review_date === next_review_date
        })
      } catch (verifyError) {
        console.error('❌ [DEBUG] 验证数据库更新失败:', verifyError)
      }
    } else if (actionType === 'failed') {
      const record = existingRecord.data
      console.log('📖 [DEBUG] 复习单词失败 - 更新前状态:', {
        word,
        当前等级: record.level,
        当前复习日期: record.next_review_date,
        今天: todayString
      })

      const { level, next_review_date } = calculateNextReviewTime(record.level, false)
      console.log('📖 [DEBUG] 复习单词失败 - 计算新状态:', {
        新等级: level,
        新复习日期: next_review_date
      })

      await db.collection('word_records').doc(recordId).update({
        data: {
          level: level,
          next_review_date: next_review_date,
          actual_review_dates: db.command.push(todayString)
        }
      })

      console.log('✅ [DEBUG] 复习单词失败 - 数据库更新完成')

      // 验证数据库更新是否成功
      try {
        const verifyRecord = await db.collection('word_records').doc(recordId).get()
        console.log('🔍 [DEBUG] 验证数据库更新结果 (失败情况):', {
          单词: word,
          更新后等级: verifyRecord.data.level,
          更新后复习日期: verifyRecord.data.next_review_date,
          预期等级: level,
          预期复习日期: next_review_date,
          更新是否成功: verifyRecord.data.level === level && verifyRecord.data.next_review_date === next_review_date
        })
      } catch (verifyError) {
        console.error('❌ [DEBUG] 验证数据库更新失败:', verifyError)
      }
    } else if (actionType === 'remember') {
      const record = existingRecord.data
      const overdueDays = calculateOverdueDays(record.next_review_date)
      const newLevel = handleOverdueWordLevel(record.level, 'remember', overdueDays)
      const { next_review_date } = calculateNextReviewTime(newLevel - 1, true) // 减1是因为函数内部会加1

      await db.collection('word_records').doc(recordId).update({
        data: {
          level: newLevel,
          next_review_date: next_review_date,
          actual_review_dates: db.command.push(todayString)
        }
      })
    } else if (actionType === 'vague') {
      const record = existingRecord.data
      const overdueDays = calculateOverdueDays(record.next_review_date)
      const newLevel = handleOverdueWordLevel(record.level, 'vague', overdueDays)
      const { next_review_date } = calculateNextReviewTime(newLevel - 1, true) // 减1是因为函数内部会加1

      await db.collection('word_records').doc(recordId).update({
        data: {
          level: newLevel,
          next_review_date: next_review_date,
          actual_review_dates: db.command.push(todayString)
        }
      })
    } else if (actionType === 'reset') {
      const newLevel = 1 // 重置为第一级
      const { next_review_date } = calculateNextReviewTime(0, true) // 从0开始计算下次复习时间

      await db.collection('word_records').doc(recordId).update({
        data: {
          level: newLevel,
          next_review_date: next_review_date,
          actual_review_dates: db.command.push(todayString)
        }
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