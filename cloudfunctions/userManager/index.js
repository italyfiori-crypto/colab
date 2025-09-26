// 用户管理云函数
const cloud = require('wx-server-sdk')

cloud.init({
  env: cloud.DYNAMIC_CURRENT_ENV
})

const db = cloud.database()

// 图片处理工具函数
/**
 * 获取云存储文件的临时访问链接
 * @param {string|Array} fileList - 文件ID或文件ID数组
 * @returns {Promise} 临时链接结果
 */
async function getTempFileURL(fileList) {
  const files = Array.isArray(fileList) ? fileList : [fileList]
  const validFiles = files.filter(fileId => fileId && typeof fileId === 'string' && fileId.startsWith('cloud://'))

  if (validFiles.length === 0) {
    return { fileList: [] }
  }

  try {
    const result = await cloud.getTempFileURL({
      fileList: validFiles.map(fileId => ({
        fileID: fileId,
        maxAge: 86400 // 24小时有效期
      }))
    })

    console.log('✅ [DEBUG] 云端获取临时链接成功:', result.fileList.length, '个文件')
    return result
  } catch (error) {
    console.error('❌ [DEBUG] 云端获取临时链接失败:', error)
    return { fileList: [] }
  }
}

/**
 * 获取单个图片的临时链接
 * @param {string} fileId - 云存储文件ID
 * @returns {Promise<string>} 临时链接URL
 */
async function getSingleTempFileURL(fileId) {
  if (!fileId || typeof fileId !== 'string') {
    return ''
  }

  // 如果不是云存储文件ID，直接返回
  if (!fileId.startsWith('cloud://')) {
    return fileId
  }

  const result = await getTempFileURL([fileId])
  if (result.fileList && result.fileList.length > 0) {
    return result.fileList[0].tempFileURL || ''
  }
  return ''
}

/**
 * 处理用户数据中的图片字段，将fileID转换为临时链接
 * @param {Object} userData - 用户数据
 * @returns {Promise<Object>} 处理后的用户数据
 */
async function processUserImages(userData) {
  if (!userData || !userData.avatar_url) {
    return userData
  }

  try {
    const tempUrl = await getSingleTempFileURL(userData.avatar_url)
    return {
      ...userData,
      avatar_url: tempUrl || userData.avatar_url // 如果获取失败，保持原值
    }
  } catch (error) {
    console.error('❌ [DEBUG] 处理用户图片失败:', error)
    return userData
  }
}

exports.main = async (event, context) => {
  const { action, ...params } = event
  const wxContext = cloud.getWXContext()
  const userId = wxContext.OPENID

  try {
    switch (action) {
      case 'getUserInfo':
        return await getUserInfo(userId)
      case 'updateUserInfo':
        return await updateUserInfo(userId, params)
      case 'updateAvatar':
        return await updateAvatar(userId, params)
      default:
        return {
          success: false,
          message: '未知的操作类型'
        }
    }
  } catch (error) {
    console.error('用户管理云函数执行错误:', error)
    return {
      success: false,
      message: error.message || '服务器错误'
    }
  }
}

/**
 * 获取用户信息 - 不存在时自动创建
 */
async function getUserInfo(userId) {
  console.log('📋 [DEBUG] 获取用户信息:', userId)

  let userResult

  // 使用then/catch语法查询数据库，避免查不到数据时抛异常
  await db.collection('users').doc(userId).get()
    .then(res => {
      userResult = res
      console.log('✅ [DEBUG] 查询用户信息成功')
    })
    .catch(err => {
      console.error('❌ [DEBUG] 查询用户信息失败:', err)
      userResult = { data: null }
    })

  if (userResult.data) {
    console.log('✅ [DEBUG] 用户已存在，返回用户信息')

    // 处理用户头像临时链接
    const processedUserData = await processUserImages(userResult.data)

    return {
      success: true,
      data: processedUserData
    }
  }

  try {
    // 用户不存在，创建默认用户
    console.log('🆕 [DEBUG] 用户不存在，创建默认用户')
    const defaultUser = await createDefaultUser(userId)

    defaultUser['_id'] = userId
    await db.collection('users').add({
      data: defaultUser
    })

    console.log('✅ [DEBUG] 默认用户创建成功')

    // 处理新创建用户的头像
    const processedUserData = await processUserImages(defaultUser)

    return {
      success: true,
      data: processedUserData
    }
  } catch (error) {
    console.error('❌ [DEBUG] 创建用户失败:', error)
    return {
      success: false,
      message: error.message
    }
  }
}

/**
 * 生成唯一用户ID
 */
async function generateUniqueUserId() {
  const maxAttempts = 10

  for (let attempts = 0; attempts < maxAttempts; attempts++) {
    const userId = Math.floor(100000 + Math.random() * 900000)
    let existingUser

    // 使用then/catch语法查询数据库
    await db.collection('users')
      .where({ user_id: userId })
      .limit(1)
      .get()
      .then(res => {
        existingUser = res
        console.log('✅ [DEBUG] 检查用户ID成功:', userId)
      })
      .catch(err => {
        console.error('❌ [DEBUG] 检查用户ID时出错:', err)
        existingUser = { data: [] }
      })

    if (existingUser.data.length === 0) {
      console.log('✅ [DEBUG] 生成唯一用户ID:', userId)
      return userId
    }

    console.log('⚠️ [DEBUG] 用户ID冲突，重新生成:', userId)
  }

  // 如果多次尝试失败，使用时间戳后6位
  const fallbackId = parseInt(Date.now().toString().slice(-6))
  console.log('⚠️ [DEBUG] 使用后备用户ID:', fallbackId)
  return fallbackId
}

/**
 * 创建默认用户信息
 */
async function createDefaultUser(userId) {
  const randomNum = Math.floor(Math.random() * 9999).toString().padStart(4, '0')
  const uniqueUserId = await generateUniqueUserId()

  const defaultUser = {
    user_id: uniqueUserId,
    nickname: `学习者${randomNum}`,
    avatar_url: '/resource/icons/avatar.svg',

    // 阅读设置
    reading_settings: {
      subtitle_lang: '中英双语',
      playback_speed: 1.0
    },

    // 学习设置
    learning_settings: {
      voice_type: '美式发音',
      daily_word_limit: 20,
      new_word_sort: '优先新词'
    },

    created_at: Date.now(),
    updated_at: Date.now()
  }

  console.log('📝 [DEBUG] 创建的默认用户信息:', {
    userId: userId,
    user_id: uniqueUserId,
    nickname: defaultUser.nickname,
    settings: {
      reading: defaultUser.reading_settings,
      learning: defaultUser.learning_settings
    }
  })

  return defaultUser
}

/**
 * 统一更新用户信息接口（基础信息 + 设置信息）
 */
async function updateUserInfo(userId, { userInfo }) {
  console.log('🔄 [DEBUG] 统一更新用户信息:', { userId, userInfo })

  const updateData = {
    updated_at: Date.now()
  }

  // 处理用户基础信息
  if (userInfo.nickname) {
    // 简单的昵称验证
    if (userInfo.nickname.length > 20) {
      return {
        success: false,
        message: '昵称不能超过20个字符'
      }
    }
    updateData.nickname = userInfo.nickname.trim()
  }

  if (userInfo.avatar_url) {
    updateData.avatar_url = userInfo.avatar_url
  }

  // 处理用户设置信息
  if (userInfo.reading_settings) {
    updateData.reading_settings = userInfo.reading_settings
  }

  if (userInfo.learning_settings) {
    updateData.learning_settings = userInfo.learning_settings
  }

  try {
    await db.collection('users').doc(userId).update({
      data: updateData
    })

    console.log('✅ [DEBUG] 用户信息统一更新成功')
    return {
      success: true,
      message: '用户信息更新成功'
    }
  } catch (error) {
    console.error('❌ [DEBUG] 统一更新用户信息失败:', error)
    return {
      success: false,
      message: error.message
    }
  }
}

/**
 * 更新用户头像（使用已上传的fileID）
 * @param {string} userId - 用户ID
 * @param {Object} params - 参数对象
 * @param {string} params.fileID - 云存储文件ID
 * @returns {Promise<Object>} 更新结果
 */
async function updateAvatar(userId, { fileID }) {
  console.log('🔄 [DEBUG] 开始更新用户头像:', { userId, fileID })

  try {
    // 验证fileID格式
    if (!fileID || typeof fileID !== 'string' || !fileID.startsWith('cloud://')) {
      throw new Error('无效的文件ID')
    }

    // 获取临时访问链接
    const tempUrl = await getSingleTempFileURL(fileID)
    console.log('🔗 [DEBUG] 获取头像临时链接:', tempUrl)

    // 更新用户表中的头像URL
    await db.collection('users').doc(userId).update({
      data: {
        avatar_url: fileID, // 保存fileID用于数据库
        updated_at: Date.now()
      }
    })

    console.log('✅ [DEBUG] 用户头像更新成功')
    return {
      success: true,
      avatarUrl: tempUrl || fileID, // 返回临时链接用于显示
      fileID: fileID,
      message: '头像更新成功'
    }
  } catch (error) {
    console.error('❌ [DEBUG] 头像更新失败:', error)
    return {
      success: false,
      message: '头像更新失败: ' + error.message
    }
  }
}