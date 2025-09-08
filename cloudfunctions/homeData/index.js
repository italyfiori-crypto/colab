// 云函数入口文件
const cloud = require('wx-server-sdk')

cloud.init({ env: cloud.DYNAMIC_CURRENT_ENV }) // 使用当前云环境

const db = cloud.database()

// 时间戳工具函数
function getNowTimestamp() {
  return Date.now()
}

// 写死的分类列表（后期可调整为数据库读取）
const CATEGORY_LIST = [
  { name: '文学名著', active: true },
  { name: '商务英语', active: false },
  { name: '影视剧本', active: false },
  { name: '新闻', active: false }
]

// 分类名称到数据库字段的映射
const CATEGORY_MAPPING = {
  '文学名著': 'literature',
  '商务英语': 'business',
  '影视剧本': 'script',
  '新闻': 'news'
}

// 最近阅读列表最大长度
const MAX_RECENT_BOOKS = 10

exports.main = async (event, context) => {
  const { type, category, keyword, book_id } = event
  const { OPENID } = cloud.getWXContext()
  const user_id = OPENID

  try {
    switch (type) {
      case 'getRecentBooks':
        return await getRecentBooks(user_id)
      case 'getCategoryBooks':
        return await getCategoryBooks(category)
      case 'searchBooks':
        return await searchBooks(keyword)
      case 'getHomeData':
        return await getHomeData(user_id, category)
      case 'addToRecent':
        return await addToRecentBooks(user_id, book_id)
      default:
        throw new Error('Unknown type: ' + type)
    }
  } catch (err) {
    console.error('homeData云函数错误:', err)
    return {
      code: -1,
      message: err.message,
      data: null
    }
  }
}

// 获取最近学习书籍
async function getRecentBooks(user_id) {
  if (!user_id) {
    return { code: 0, data: [] }
  }

  const progressResult = await db.collection('user_progress')
    .where({
      user_id: user_id
    })
    .orderBy('updated_at', 'desc')
    .limit(MAX_RECENT_BOOKS)
    .get()

  if (progressResult.data.length === 0) {
    return { code: 0, data: [] }
  }

  const bookIds = progressResult.data.map(p => p.book_id)
  const booksResult = await db.collection('books')
    .where({
      _id: db.command.in(bookIds),
      is_active: true
    })
    .get()

  const recentBooks = []
  for (const progress of progressResult.data) {
    const book = booksResult.data.find(b => b._id === progress.book_id)
    if (book) {
      const progressPercent = book.total_chapters > 0
        ? Math.round((progress.chapters_completed.length / book.total_chapters) * 100)
        : 0

      recentBooks.push({
        _id: book._id,
        title: book.title,
        author: book.author,
        cover_url: book.cover_url,
        progress: progressPercent
      })
    }
  }

  return { code: 0, data: recentBooks }
}

// 获取分类书籍
async function getCategoryBooks(categoryName = '文学名著') {
  const result = await db.collection('books')
    .where({
      category: categoryName,
      is_active: true
    })
    .orderBy('created_at', 'desc')
    .limit(20)
    .get()

  const books = result.data.map(book => ({
    _id: book._id,
    title: book.title,
    author: book.author,
    cover_url: book.cover_url,
    category: book.category,
    difficulty: book.difficulty,
    total_chapters: book.total_chapters
  }))

  return { code: 0, data: books }
}

// 搜索书籍
async function searchBooks(keyword) {
  if (!keyword) {
    return { code: 0, data: [] }
  }

  const result = await db.collection('books')
    .where({
      is_active: true,
      $or: [
        { title: db.RegExp({ regexp: keyword, options: 'i' }) },
        { author: db.RegExp({ regexp: keyword, options: 'i' }) },
        { description: db.RegExp({ regexp: keyword, options: 'i' }) }
      ]
    })
    .limit(50)
    .get()

  const books = result.data.map(book => ({
    _id: book._id,
    title: book.title,
    author: book.author,
    cover_url: book.cover_url,
    category: book.category
  }))

  return { code: 0, data: books }
}

// 一次性获取首页数据
async function getHomeData(user_id, categoryName) {
  const [recentResult, categoryResult] = await Promise.all([
    getRecentBooks(user_id),
    getCategoryBooks(categoryName || CATEGORY_LIST[0].name)
  ])

  return {
    code: 0,
    data: {
      recentBooks: recentResult.data,
      categoryBooks: categoryResult.data,
      categories: CATEGORY_LIST
    }
  }
}

// 添加到最近阅读
async function addToRecentBooks(user_id, book_id) {
  console.log('🔄 [DEBUG] 开始添加到最近阅读:', { user_id, book_id })

  if (!user_id || !book_id) {
    console.log('❌ [DEBUG] 参数不完整:', { user_id, book_id })
    return { code: -1, message: '参数不完整' }
  }

  try {
    // 1. 检查书籍是否存在且有效
    console.log('📤 [DEBUG] 查询书籍:', book_id)
    const bookResult = await db.collection('books')
      .doc(book_id)
      .get()

    console.log('📥 [DEBUG] 书籍查询结果:', bookResult)

    if (!bookResult.data) {
      console.log('❌ [DEBUG] 书籍不存在:', book_id)
      return { code: -1, message: '书籍不存在' }
    }

    if (!bookResult.data.is_active) {
      console.log('❌ [DEBUG] 书籍已下架:', book_id)
      return { code: -1, message: '书籍已下架' }
    }

    console.log('✅ [DEBUG] 书籍验证通过:', book_id)

    // 2. 检查是否已存在user_progress记录
    const progressId = `${user_id}_${book_id}`
    console.log('🔄 [DEBUG] 进度记录ID:', progressId)

    // 使用where查询而不是doc.get()，避免文档不存在时的错误
    let existingProgressResult = null
    await db.collection('user_progress').doc(progressId).get().then(res => {
      existingProgressResult = res
      console.log('✅ [DEBUG] 查询现有进度记录成功:', res)
    }).catch(err => {
      console.error('❌ [DEBUG] 查询现有进度记录失败:', err)
    })

    const now = getNowTimestamp()
    if (existingProgressResult) {
      // 3. 如果已存在，只更新最后访问时间
      console.log('🔄 [DEBUG] 更新现有进度记录')
      await db.collection('user_progress')
        .doc(progressId)
        .update({
          data: {
            updated_at: now
          }
        }).then(res => {
          console.log('✅ [DEBUG] 更新现有进度记录成功:', res)
        }).catch(err => {
          console.error('❌ [DEBUG] 更新现有进度记录失败:', err)
        })
    } else {
      // 4. 如果不存在，创建新的进度记录
      console.log('🆕 [DEBUG] 创建新的进度记录')
      await db.collection('user_progress')
        .add({
          data: {
            _id: progressId,
            user_id: user_id,
            book_id: book_id,
            current_chapter: 0,
            chapters_completed: [],
            created_at: now,
            updated_at: now
          }
        }).then(res => {
          console.log('✅ [DEBUG] 创建新的进度记录成功:', res)
        }).catch(err => {
          console.error('❌ [DEBUG] 创建新的进度记录失败:', err)
        })
    }

    // 5. 清理超过最大数量的旧记录
    console.log('🧹 [DEBUG] 开始清理旧记录')
    await cleanupOldRecentBooks(user_id)

    console.log('✅ [DEBUG] 添加到最近阅读成功')
    return { code: 0, message: '添加到最近阅读成功' }

  } catch (err) {
    console.error('❌ [DEBUG] 添加到最近阅读失败:', err)
    return { code: -1, message: err.message || '添加到最近阅读失败' }
  }
}

// 清理旧的最近阅读记录
async function cleanupOldRecentBooks(user_id) {
  try {
    console.log('🧹 [DEBUG] 开始清理用户旧记录:', user_id)

    // 查询该用户的所有进度记录，按更新时间倒序
    const allProgress = await db.collection('user_progress')
      .where({
        user_id: user_id
      })
      .orderBy('updated_at', 'desc')
      .get()

    console.log('📥 [DEBUG] 用户进度记录总数:', allProgress.data.length)

    // 如果超过最大数量，删除多余的记录
    if (allProgress.data.length > MAX_RECENT_BOOKS) {
      const toDelete = allProgress.data.slice(MAX_RECENT_BOOKS)
      console.log('🗑️ [DEBUG] 需要删除的记录数:', toDelete.length)

      for (const record of toDelete) {
        console.log('🗑️ [DEBUG] 删除记录:', record._id)
        await db.collection('user_progress')
          .doc(record._id)
          .remove()
      }

      console.log(`✅ [DEBUG] 清理了 ${toDelete.length} 条旧的阅读记录`)
    } else {
      console.log('✅ [DEBUG] 无需清理，记录数未超过限制')
    }
  } catch (err) {
    console.error('❌ [DEBUG] 清理旧记录失败:', err)
    // 不影响主流程，只记录错误
  }
}