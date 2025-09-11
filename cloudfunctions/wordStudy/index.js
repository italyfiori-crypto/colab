// 单词学习云函数
const cloud = require('wx-server-sdk')

cloud.init({
  env: cloud.DYNAMIC_CURRENT_ENV
})

const db = cloud.database()

// 中国时区偏移 (UTC+8)
const CHINA_TIMEZONE_OFFSET_HOURS = 8

// 时间戳和日期工具函数
function getNowTimestamp() {
  return Date.now()
}

function getTodayString() {
  // 使用中国时区 (UTC+8)
  const now = new Date()
  const chinaTime = new Date(now.getTime() + (CHINA_TIMEZONE_OFFSET_HOURS * 60 * 60 * 1000))
  const year = chinaTime.getUTCFullYear()
  const month = String(chinaTime.getUTCMonth() + 1).padStart(2, '0')
  const day = String(chinaTime.getUTCDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

function addDaysToToday(days) {
  // 使用中国时区 (UTC+8)
  const now = new Date()
  const chinaTime = new Date(now.getTime() + (CHINA_TIMEZONE_OFFSET_HOURS * 60 * 60 * 1000))
  chinaTime.setUTCDate(chinaTime.getUTCDate() + days)
  const year = chinaTime.getUTCFullYear()
  const month = String(chinaTime.getUTCMonth() + 1).padStart(2, '0')
  const day = String(chinaTime.getUTCDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

// 艾宾浩斯复习间隔 (当前等级进入下一等级需要的天数)
const REVIEW_INTERVALS = [1, 2, 4, 7, 15, 30, 36500]
const MAX_LEVEL = REVIEW_INTERVALS.length - 1
const MAX_DAILY_NEW = 20

exports.main = async (event, context) => {
  const { action, ...params } = event
  const wxContext = cloud.getWXContext()
  const userId = wxContext.OPENID

  try {
    switch (action) {
      case 'getStudyStats':
        return await getStudyStats(userId, params)
      case 'getWordList':
        return await getWordList(userId, params)
      case 'updateWordRecord':
        return await updateWordRecord(userId, params)
      case 'getWordsByDate':
        return await getWordsByDate(userId, params)
      case 'getDailyStats':
        return await getDailyStats(userId, params)
      case 'updateDailyStats':
        return await updateDailyStats(userId, params)
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
function calcNextReviewDate(cur_level) {
  // 新词从1级开始（第一次复习），已学词汇等级+1但不超过最大等级
  const newLevel = cur_level == null ? 0 : Math.min(cur_level + 1, MAX_LEVEL)

  return {
    level: newLevel,
    next_review_date: addDaysToToday(REVIEW_INTERVALS[newLevel]) // 数组从0开始，level从1开始
  }
}

// 计算逾期天数
function calculateOverdueDays(nextReviewDate) {
  const todayString = getTodayString()

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
async function getStudyStats(userId, { dailyWordLimit } = {}) {
  const todayString = getTodayString()

  // 参数验证和默认值处理
  let dailyLimit = MAX_DAILY_NEW
  if (dailyWordLimit !== undefined && dailyWordLimit !== null) {
    // 确保是有效的正整数
    const parsedLimit = parseInt(dailyWordLimit)
    if (parsedLimit > 0 && parsedLimit <= 100) { // 合理范围限制
      dailyLimit = parsedLimit
    }
  }

  console.log("todayString:", todayString, "dailyLimit:", dailyLimit, "原始参数:", dailyWordLimit)

  // 计算今日已学习的新单词数量（今日首次学习的单词）
  const studiedTodayResult = await db.collection('word_records')
    .where({
      user_id: userId,
      first_learn_date: todayString,
    })
    .count()

  const studiedToday = studiedTodayResult.total
  const maxRemainingToday = Math.max(0, dailyLimit - studiedToday)

  // 如果今日配额已满，待学习数量为0
  let newWordsCount = 0
  if (maxRemainingToday > 0) {
    // 统计所有未学习的新单词数（level为null且first_learn_date为null）
    const totalNewWordsResult = await db.collection('word_records')
      .where({
        user_id: userId,
        level: null,
        first_learn_date: null
      })
      .count()

    // 返回实际可学习的数量（总数与剩余配额的较小值）
    newWordsCount = Math.min(totalNewWordsResult.total, maxRemainingToday)
  }

  // 统计今日需复习单词数
  const reviewWordsResult = await db.collection('word_records')
    .where({
      user_id: userId,
      level: db.command.lt(MAX_LEVEL),
      next_review_date: todayString
    })
    .count()

  // 统计逾期单词数
  const overdueWordsResult = await db.collection('word_records')
    .where({
      user_id: userId,
      level: db.command.lt(MAX_LEVEL),
      next_review_date: db.command.lt(todayString)
    })
    .count()

  return {
    success: true,
    data: {
      newWordsCount: newWordsCount,
      reviewWordsCount: reviewWordsResult.total,
      overdueWordsCount: overdueWordsResult.total
    }
  }
}

// 获取指定类型的单词列表  
async function getWordList(userId, { type, limit = 50, dailyWordLimit, sortOrder }) {
  const todayString = getTodayString()

  // 参数验证和默认值处理
  let validLimit = 50
  if (limit !== undefined && limit !== null) {
    const parsedLimit = parseInt(limit)
    if (parsedLimit > 0 && parsedLimit <= 200) { // 合理范围限制
      validLimit = parsedLimit
    }
  }

  let validSortOrder = 'asc'
  if (sortOrder && ['asc', 'desc'].includes(sortOrder)) {
    validSortOrder = sortOrder
  }

  console.log(`🔍 [DEBUG] getWordList参数验证: type=${type}, limit=${validLimit}, dailyWordLimit=${dailyWordLimit}, sortOrder=${validSortOrder}`)

  let query

  switch (type) {
    case 'new':
      // 参数验证和默认值处理
      let maxDailyNew = MAX_DAILY_NEW
      if (dailyWordLimit !== undefined && dailyWordLimit !== null) {
        const parsedLimit = parseInt(dailyWordLimit)
        if (parsedLimit > 0 && parsedLimit <= 100) {
          maxDailyNew = parsedLimit
        }
      }

      // 计算今日已学习的新单词数量（今日首次学习的单词）
      const studiedTodayResult = await db.collection('word_records')
        .where({
          user_id: userId,
          first_learn_date: todayString,
        })
        .count()

      const studiedToday = studiedTodayResult.total
      const maxRemainingToday = Math.max(0, maxDailyNew - studiedToday)

      console.log(`🔄 [DEBUG] 今日新学单词统计: 已学${studiedToday}个，剩余${maxRemainingToday}个，上限${maxDailyNew}个`)

      if (maxRemainingToday === 0) {
        return {
          success: true,
          data: []
        }
      }

      // 获取未学习的新单词（level为null且first_learn_date为null）
      query = db.collection('word_records')
        .where({
          user_id: userId,
          level: null,
          first_learn_date: null
        })
        .orderBy('created_at', 'asc') // 固定排序确保每次进入看到相同顺序
        .limit(Math.min(maxRemainingToday, validLimit))
      break

    case 'review':
      query = db.collection('word_records')
        .where({
          user_id: userId,
          level: db.command.lt(MAX_LEVEL),
          next_review_date: todayString
        })
        .orderBy('updated_at', validSortOrder)
        .limit(validLimit)

      console.log(`🔄 [DEBUG] 复习单词排序方式: ${validSortOrder}`)
      break

    case 'overdue':
      query = db.collection('word_records')
        .where({
          user_id: userId,
          level: db.command.lt(MAX_LEVEL),
          next_review_date: db.command.lt(todayString)
        })
        .orderBy('updated_at', validSortOrder)
        .limit(validLimit)

      console.log(`🔄 [DEBUG] 逾期单词排序方式: ${validSortOrder}`)
      break

    default:
      throw new Error('无效的单词类型')
  }

  const wordsResult = await query.get()
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

  // 处理单词记录并匹配词汇详情，保持原有排序
  const words = wordsResult.data
    .filter(record => record.word_id && vocabularyMap.has(record.word_id))
    .map(record => {
      const vocab = vocabularyMap.get(record.word_id)

      let wordData = {
        id: record._id,
        word_id: record.word_id,
        word: vocab.word,
        phonetic_uk: vocab.phonetic_uk,
        phonetic_us: vocab.phonetic_us,
        audio_url_uk: vocab.audio_url_uk,
        audio_url_us: vocab.audio_url_us,
        translations: vocab.translation.slice(0, 3).map(t => ({
          partOfSpeech: t.type,
          meaning: t.meaning
        })),
        // 保留原始记录的排序字段
        updated_at: record.updated_at,
        created_at: record.created_at
      }

      // 如果是逾期单词，添加逾期天数
      if (type === 'overdue') {
        wordData.overdue_days = calculateOverdueDays(record.next_review_date)
      }

      return wordData
    })

  // 根据类型和排序参数重新排序，确保排序生效
  if (type === 'review' || type === 'overdue') {
    words.sort((a, b) => {
      if (validSortOrder === 'asc') {
        return new Date(a.updated_at) - new Date(b.updated_at)
      } else {
        return new Date(b.updated_at) - new Date(a.updated_at)
      }
    })
    console.log(`🔄 [DEBUG] ${type}单词已重新排序: ${validSortOrder}, 首个单词更新时间: ${words[0]?.updated_at}`)
  } else if (type === 'new') {
    words.sort((a, b) => {
      if (validSortOrder === 'asc') {
        return new Date(a.created_at) - new Date(b.created_at)
      } else {
        return new Date(b.created_at) - new Date(a.created_at)
      }
    })
    console.log(`🔄 [DEBUG] 新学单词已重新排序: ${validSortOrder}, 首个单词创建时间: ${words[0]?.created_at}`)
  }

  console.log('📊 [DEBUG] 成功处理单词数量:', words.length, '原始记录数:', wordsResult.data.length)

  return {
    success: true,
    data: words
  }
}

// 更新单词记录
async function updateWordRecord(userId, { word_id, actionType }) {
  const nowTimestamp = getNowTimestamp()
  const todayString = getTodayString()

  console.log('📖 [DEBUG] updateWordRecord云函数开始执行:', { userId, word_id, actionType })
  try {
    // 使用user_id和word_id查找现有记录（安全查询）
    const queryResult = await db.collection('word_records')
      .where({
        user_id: userId,
        word_id: word_id
      })
      .get()

    let existingRecord = { data: null }
    let recordId = null

    if (queryResult.data.length > 0) {
      existingRecord = { data: queryResult.data[0] }
      recordId = queryResult.data[0]._id
    } else {
      // 如果记录不存在，创建新的recordId
      recordId = `${userId}_${word_id}`
    }

    const record = existingRecord.data

    if (actionType === 'start') {
      // 开始学习新单词
      const { level, next_review_date } = calcNextReviewDate(null)

      console.log('📖 [DEBUG] 开始学习新单词，计算结果:', {
        level,
        next_review_date,
        existingRecord: !!existingRecord.data
      })

      if (existingRecord.data) {
        // 更新现有记录
        console.log('📖 [DEBUG] 更新现有记录:', recordId)
        await db.collection('word_records').doc(recordId).update({
          data: {
            level: level,
            first_learn_date: todayString,
            next_review_date: next_review_date,
            actual_learn_dates: db.command.push(todayString),
            updated_at: nowTimestamp
          }
        })
      } else {
        // 创建新记录
        console.log('📖 [DEBUG] 创建新记录:', recordId)
        await db.collection('word_records').doc(recordId).set({
          data: {
            user_id: userId,
            word_id: word_id,
            level: level,
            first_learn_date: todayString,
            next_review_date: next_review_date,
            actual_learn_dates: [todayString],
            actual_review_dates: [],
            created_at: nowTimestamp,
            updated_at: nowTimestamp
          }
        })
      }

      console.log('✅ [DEBUG] 新学单词状态更新完成:', { level, first_learn_date: todayString, next_review_date })

      // 同步更新每日学习统计
      await updateDailyStatsSync(userId, todayString, 'learn')
    } else if (actionType === 'review') {
      const { level: new_level, next_review_date } = calcNextReviewDate(record.level)
      await db.collection('word_records').doc(recordId).update({
        data: {
          level: new_level,
          next_review_date: next_review_date,
          actual_review_dates: db.command.push(todayString),
          updated_at: nowTimestamp
        }
      })

      // 同步更新每日学习统计
      await updateDailyStatsSync(userId, todayString, 'review')

      console.log('✅ [DEBUG] 复习单词成功 - 数据库更新完成')
    } else if (actionType === 'remember') {
      const record = existingRecord.data
      const overdueDays = calculateOverdueDays(record.next_review_date)
      const newLevel = handleOverdueWordLevel(record.level, 'remember', overdueDays)
      const { next_review_date } = calcNextReviewDate(newLevel)

      await db.collection('word_records').doc(recordId).update({
        data: {
          level: newLevel,
          next_review_date: next_review_date,
          actual_review_dates: db.command.push(todayString),
          updated_at: nowTimestamp
        }
      })

      // 同步更新每日学习统计
      await updateDailyStatsSync(userId, todayString, 'review')
    } else if (actionType === 'vague') {
      const record = existingRecord.data
      const overdueDays = calculateOverdueDays(record.next_review_date)
      const newLevel = handleOverdueWordLevel(record.level, 'vague', overdueDays)

      // vague情况下使用更短的复习间隔，不提升等级，使用当前等级的复习间隔
      const nextReviewDateString = addDaysToToday(REVIEW_INTERVALS[Math.max(0, newLevel - 1)])

      await db.collection('word_records').doc(recordId).update({
        data: {
          level: newLevel,
          next_review_date: nextReviewDateString,
          actual_review_dates: db.command.push(todayString),
          updated_at: nowTimestamp
        }
      })

      // 同步更新每日学习统计
      await updateDailyStatsSync(userId, todayString, 'review')
    } else if (actionType === 'reset') {
      // 重置为第一级
      const { level, next_review_date } = calcNextReviewDate(null)

      await db.collection('word_records').doc(recordId).update({
        data: {
          level: level,
          next_review_date: next_review_date,
          actual_review_dates: db.command.push(todayString),
          updated_at: nowTimestamp
        }
      })

      // 同步更新每日学习统计
      await updateDailyStatsSync(userId, todayString, 'review')
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

// 根据日期获取单词记录
async function getWordsByDate(userId, { date, type }) {
  try {
    console.log('📅 [DEBUG] 查询日期单词记录:', { date, type, userId })

    let query

    if (type === 'learned') {
      // 获取指定日期学习的单词（actual_learn_dates数组包含该日期）
      query = db.collection('word_records')
        .where({
          user_id: userId,
          actual_learn_dates: db.command.all([date])
        })
        .orderBy('updated_at', 'asc')
    } else if (type === 'reviewed') {
      // 获取指定日期复习的单词（实际复习日期数组包含该日期）
      query = db.collection('word_records')
        .where({
          user_id: userId,
          actual_review_dates: db.command.all([date])
        })
        .orderBy('updated_at', 'asc')
    } else {
      throw new Error('无效的查询类型')
    }

    const wordsResult = await query.get()

    if (wordsResult.data.length === 0) {
      console.log('📝 [DEBUG] 指定日期没有找到单词记录')
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

        return {
          id: record._id,
          word_id: record.word_id,  // 添加word_id字段
          word: vocab.word,
          phonetic: vocab.phonetic_us || vocab.phonetic_uk || vocab.phonetic,
          audioUrl: vocab.audio_url_us || vocab.audio_url || vocab.audio_url_uk,
          translations: vocab.translation.slice(0, 3).map(t => ({
            partOfSpeech: t.type,
            meaning: t.meaning
          }))
        }
      })

    console.log('📊 [DEBUG] 成功处理单词数量:', words.length, '原始记录数:', wordsResult.data.length)

    return {
      success: true,
      data: words
    }
  } catch (error) {
    console.error('查询日期单词记录失败:', error)
    return {
      success: false,
      message: error.message || '查询失败'
    }
  }
}

// 计算学习强度等级（0-4）
function calculateIntensityLevel(learnedCount, reviewedCount) {
  // 计算学习强度 (基数20)
  let learnIntensity;
  if (learnedCount === 0) learnIntensity = 0;
  else if (learnedCount <= 5) learnIntensity = 1;   // 1-5个
  else if (learnedCount <= 10) learnIntensity = 2;  // 6-10个
  else if (learnedCount <= 15) learnIntensity = 3;  // 11-15个
  else learnIntensity = 4;                          // 16+个

  // 计算复习强度 (基数120)
  let reviewIntensity;
  if (reviewedCount === 0) reviewIntensity = 0;
  else if (reviewedCount <= 30) reviewIntensity = 1;   // 1-30个
  else if (reviewedCount <= 60) reviewIntensity = 2;   // 31-60个
  else if (reviewedCount <= 90) reviewIntensity = 3;   // 61-90个
  else reviewIntensity = 4;                            // 91+个

  // 取最大值
  return Math.max(learnIntensity, reviewIntensity);
}

// 同步更新每日学习统计（内部函数）
async function updateDailyStatsSync(userId, date, actionType) {
  try {
    const recordId = `${userId}_${date}`
    const nowTimestamp = getNowTimestamp()

    // 查找或创建当日统计记录
    let existingStats
    try {
      existingStats = await db.collection('daily_stats').doc(recordId).get()
    } catch (error) {
      existingStats = { data: null }
    }

    if (existingStats.data) {
      // 更新现有记录
      const updateData = {
        updated_at: nowTimestamp
      }

      if (actionType === 'learn') {
        updateData.learned_count = (existingStats.data.learned_count || 0) + 1
      } else if (actionType === 'review') {
        updateData.reviewed_count = (existingStats.data.reviewed_count || 0) + 1
      }

      await db.collection('daily_stats').doc(recordId).update({
        data: updateData
      })
    } else {
      // 创建新记录
      const newStats = {
        user_id: userId,
        date: date,
        learned_count: actionType === 'learn' ? 1 : 0,
        reviewed_count: actionType === 'review' ? 1 : 0,
        created_at: nowTimestamp,
        updated_at: nowTimestamp
      }

      await db.collection('daily_stats').doc(recordId).set({
        data: newStats
      })
    }

    console.log('✅ [DEBUG] 每日统计更新成功:', { userId, date, actionType })
  } catch (error) {
    console.error('❌ [DEBUG] 更新每日统计失败:', error)
  }
}

// 获取用户每日学习统计
async function getDailyStats(userId, { startDate, endDate }) {
  try {
    console.log('📊 [DEBUG] 查询每日学习统计:', { userId, startDate, endDate })

    // 构建查询条件
    let whereCondition = {
      user_id: userId
    }

    // 如果提供了日期范围，添加日期筛选
    if (startDate && endDate) {
      whereCondition.date = db.command.gte(startDate).and(db.command.lte(endDate))
    } else if (startDate) {
      whereCondition.date = db.command.gte(startDate)
    } else if (endDate) {
      whereCondition.date = db.command.lte(endDate)
    }

    let query = db.collection('daily_stats').where(whereCondition)

    // 首先检查集合是否存在
    try {
      const result = await query.orderBy('date', 'desc').limit(100).get()
      console.log('📈 [DEBUG] 每日统计查询完成，记录数:', result.data.length)

      return {
        success: true,
        data: result.data
      }
    } catch (dbError) {
      // 如果是集合不存在的错误，返回空数据而不是错误
      if (dbError.message && dbError.message.includes('collection')) {
        console.warn('⚠️ [WARN] daily_stats集合不存在，返回空数据')
        return {
          success: true,
          data: []
        }
      }
      throw dbError // 重新抛出其他错误
    }
  } catch (error) {
    console.error('查询每日统计失败:', error)
    // 降级方案：返回空数据，而不是完全失败
    return {
      success: true,
      data: [],
      message: '数据加载失败，显示默认状态'
    }
  }
}

// 手动更新每日学习统计（供外部调用）
async function updateDailyStats(userId, { date, learned_count, reviewed_count }) {
  try {
    const recordId = `${userId}_${date}`
    const nowTimestamp = getNowTimestamp()

    const statsData = {
      user_id: userId,
      date: date,
      learned_count: learned_count || 0,
      reviewed_count: reviewed_count || 0,
      updated_at: nowTimestamp
    }

    // 尝试更新，如果不存在则创建
    try {
      await db.collection('daily_stats').doc(recordId).update({
        data: statsData
      })
    } catch (error) {
      // 记录不存在，创建新记录
      statsData.created_at = nowTimestamp
      await db.collection('daily_stats').doc(recordId).set({
        data: statsData
      })
    }

    console.log('✅ [DEBUG] 手动更新每日统计成功:', statsData)

    return {
      success: true,
      message: '统计更新成功'
    }
  } catch (error) {
    console.error('更新每日统计失败:', error)
    return {
      success: false,
      message: error.message || '更新失败'
    }
  }
}