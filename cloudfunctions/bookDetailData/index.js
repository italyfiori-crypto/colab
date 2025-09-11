// 云函数入口文件
const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV }) // 使用当前云环境

const db = cloud.database()

// 过滤选项常量
const FILTER_OPTIONS = [
  { value: 'all', label: '全部章节' },
  { value: 'completed', label: '已学习' },
  { value: 'available', label: '可学习' }
]

exports.main = async (event, context) => {
  const { bookId, page = 1, pageSize = 20 } = event
  const { OPENID } = cloud.getWXContext()
  const user_id = OPENID

  console.log('📖 [DEBUG] bookDetailData云函数开始执行:', { bookId, user_id, page, pageSize })

  try {
    const result = await getBookDetail(bookId, user_id, page, pageSize)
    console.log('✅ [DEBUG] bookDetailData云函数执行成功:', result.code === 0 ? '成功' : result.message)
    return result
  } catch (err) {
    console.error('❌ [DEBUG] bookDetailData云函数错误:', err)
    return {
      code: -1,
      message: err.message,
      data: null
    }
  }
}

// 获取书籍详情数据
async function getBookDetail(bookId, user_id, page = 1, pageSize = 20) {
  console.log('🔄 [DEBUG] 开始获取书籍详情:', { bookId, user_id, page, pageSize })

  // 参数验证
  if (!bookId) {
    console.log('❌ [DEBUG] 参数验证失败: 缺少书籍ID')
    return {
      code: -1,
      message: '缺少书籍ID参数'
    }
  }

  // 1. 获取书籍基本信息
  console.log('📤 [DEBUG] 查询书籍基本信息:', bookId)
  let bookResult = null
  await db.collection('books').doc(bookId).get().then(res => {
    bookResult = res
    console.log('📥 [DEBUG] 书籍查询结果:', bookResult)
  }).catch(err => {
    console.log('❌ [DEBUG] 书籍查询失败:', bookId, err.message)
  })

  if (!bookResult || !bookResult.data) {
    console.log('❌ [DEBUG] 书籍不存在:', bookId)
    return {
      code: -1,
      message: '书籍不存在'
    }
  }

  if (!bookResult.data.is_active) {
    console.log('❌ [DEBUG] 书籍已下架:', bookId)
    return {
      code: -1,
      message: '书籍已下架'
    }
  }

  const book = bookResult.data
  console.log('✅ [DEBUG] 书籍验证通过:', { title: book.title, total_chapters: book.total_chapters })

  // 2. 获取章节列表（支持分页）
  const currentPage = Math.max(1, parseInt(page) || 1)
  const limit = Math.min(50, Math.max(1, parseInt(pageSize) || 20))
  const skip = (currentPage - 1) * limit

  console.log('📤 [DEBUG] 查询章节列表:', { bookId, currentPage, limit, skip })
  
  // 查询章节时多取1条用于判断是否还有更多数据
  const chaptersResult = await db.collection('chapters')
    .where({
      book_id: bookId,
      is_active: true
    })
    .orderBy('chapter_number', 'asc')
    .skip(skip)
    .limit(limit + 1)
    .get()

  // 判断是否有更多章节
  const hasMoreChapters = chaptersResult.data.length > limit
  const actualChapters = hasMoreChapters ? chaptersResult.data.slice(0, limit) : chaptersResult.data

  console.log('📥 [DEBUG] 章节查询结果:', { 
    total: chaptersResult.data.length, 
    returned: actualChapters.length,
    hasMore: hasMoreChapters 
  })

  // 3. 获取用户学习进度（如果用户已登录）
  let userProgress = null
  const progressId = `${user_id}_${bookId}`
  console.log('📤 [DEBUG] 查询用户学习进度:', progressId)

  await db.collection('user_progress').doc(progressId).get().then(res => {
    if (res.data) {
      userProgress = res.data
      console.log('📥 [DEBUG] 用户进度查询结果:', {
        current_chapter: userProgress.current_chapter,
        chapter_progress_count: Object.keys(userProgress.chapter_progress || {}).length
      })
    } else {
      console.log('📥 [DEBUG] 用户进度为空，使用默认值')
    }
  }).catch(err => {
    console.log('📥 [DEBUG] 用户学习进度不存在，使用默认值:', err.message)
  })

  // 4. 计算用户进度 - 基于已完成的章节数量
  let completedChaptersCount = 0
  if (userProgress && userProgress.chapter_progress) {
    completedChaptersCount = Object.values(userProgress.chapter_progress)
      .filter(progress => progress.completed).length
  }

  const progressPercent = book.total_chapters > 0
    ? Math.round((completedChaptersCount / book.total_chapters) * 100)
    : 0

  console.log('📊 [DEBUG] 计算学习进度:', {
    completed: completedChaptersCount,
    total: book.total_chapters,
    percent: progressPercent
  })

  // 5. 为书籍添加进度信息，保持原有字段
  const bookInfo = {
    ...book,
    progress: progressPercent
  }

  // 6. 为章节添加学习状态 - 使用新的chapter_progress结构
  console.log('🔄 [DEBUG] 开始处理章节状态')
  const chapters = actualChapters.map(chapter => {
    const chapterProgress = userProgress && userProgress.chapter_progress
      ? userProgress.chapter_progress[chapter._id]
      : null

    let status, progress = 0

    if (chapterProgress) {
      if (chapterProgress.completed) {
        status = 'completed'
        progress = 100
      } else if (chapterProgress.time > 0) {
        status = 'in-progress'
        // 计算真实进度百分比
        progress = chapter.duration > 0
          ? Math.round((chapterProgress.time / chapter.duration) * 100)
          : 0
      } else {
        status = 'available'
        progress = 0
      }
    } else {
      status = 'available'
      progress = 0
    }

    return {
      ...chapter,
      status,
      progress
    }
  })

  const statusCounts = {
    completed: chapters.filter(c => c.status === 'completed').length,
    'in-progress': chapters.filter(c => c.status === 'in-progress').length,
    available: chapters.filter(c => c.status === 'available').length,
    locked: chapters.filter(c => c.status === 'locked').length
  }

  console.log('📊 [DEBUG] 章节状态统计:', statusCounts)

  console.log('✅ [DEBUG] 书籍详情数据处理完成')

  return {
    code: 0,
    data: {
      bookInfo,
      chapters,
      filterOptions: FILTER_OPTIONS,
      hasMoreChapters,
      currentPage,
      pageSize: limit
    }
  }
}