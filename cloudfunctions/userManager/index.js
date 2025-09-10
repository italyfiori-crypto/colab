// 用户管理云函数
const cloud = require('wx-server-sdk')

cloud.init({
  env: cloud.DYNAMIC_CURRENT_ENV
})

const db = cloud.database()

exports.main = async (event, context) => {
  const { action, ...params } = event
  const wxContext = cloud.getWXContext()
  const userId = wxContext.OPENID

  try {
    switch (action) {
      case 'getUserInfo':
        return await getUserInfo(userId)
      case 'updateUserProfile':
        return await updateUserProfile(userId, params)
      case 'updateUserSettings':
        return await updateUserSettings(userId, params)
      case 'uploadAvatar':
        return await uploadAvatar(userId, params)
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
      console.log('✅ [DEBUG] 查询用户信息成功:', res)
    })
    .catch(err => {
      console.error('❌ [DEBUG] 查询用户信息失败:', err)
      userResult = { data: null }
    })
  
  if (userResult.data) {
    console.log('✅ [DEBUG] 用户已存在，返回用户信息')
    return { 
      success: true, 
      data: userResult.data 
    }
  }
  
  try {
    // 用户不存在，创建默认用户
    console.log('🆕 [DEBUG] 用户不存在，创建默认用户')
    const defaultUser = await createDefaultUser(userId)
    
    await db.collection('users').doc(userId).set({ 
      data: defaultUser 
    })
    
    console.log('✅ [DEBUG] 默认用户创建成功')
    return { 
      success: true, 
      data: defaultUser 
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
    _id: userId,
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
      daily_word_limit: 20
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
 * 更新用户基础信息（昵称、头像）
 */
async function updateUserProfile(userId, { profileData }) {
  console.log('📝 [DEBUG] 更新用户基础信息:', { userId, profileData })
  
  const updateData = {
    updated_at: Date.now()
  }
  
  if (profileData.nickname) {
    // 简单的昵称验证
    if (profileData.nickname.length > 20) {
      return {
        success: false,
        message: '昵称不能超过20个字符'
      }
    }
    updateData.nickname = profileData.nickname.trim()
  }
  
  if (profileData.avatar_url) {
    updateData.avatar_url = profileData.avatar_url
  }
  
  try {
    await db.collection('users').doc(userId).update({
      data: updateData
    })
    
    console.log('✅ [DEBUG] 用户基础信息更新成功')
    return { 
      success: true, 
      message: '用户信息更新成功' 
    }
  } catch (error) {
    console.error('❌ [DEBUG] 更新用户基础信息失败:', error)
    return { 
      success: false, 
      message: error.message 
    }
  }
}

/**
 * 更新用户设置信息
 */
async function updateUserSettings(userId, { settingsData }) {
  console.log('⚙️ [DEBUG] 更新用户设置:', { userId, settingsData })
  
  const updateData = {
    updated_at: Date.now()
  }
  
  if (settingsData.reading_settings) {
    updateData.reading_settings = settingsData.reading_settings
  }
  
  if (settingsData.learning_settings) {
    updateData.learning_settings = settingsData.learning_settings
  }
  
  try {
    await db.collection('users').doc(userId).update({
      data: updateData
    })
    
    console.log('✅ [DEBUG] 用户设置更新成功')
    return { 
      success: true, 
      message: '设置更新成功' 
    }
  } catch (error) {
    console.error('❌ [DEBUG] 更新用户设置失败:', error)
    return { 
      success: false, 
      message: error.message 
    }
  }
}

/**
 * 上传头像到云存储
 */
async function uploadAvatar(userId, { fileContent, fileName }) {
  console.log('📷 [DEBUG] 开始上传头像:', { userId, fileName })
  
  try {
    // 生成云存储路径
    const cloudPath = `user-avatars/${userId}/${Date.now()}_${fileName || 'avatar.jpg'}`
    
    // 上传到云存储
    const uploadResult = await cloud.uploadFile({
      cloudPath: cloudPath,
      fileContent: Buffer.from(fileContent, 'base64')
    })
    
    console.log('📤 [DEBUG] 头像上传成功:', uploadResult.fileID)
    
    // 更新用户表中的头像URL
    await db.collection('users').doc(userId).update({
      data: {
        avatar_url: uploadResult.fileID,
        updated_at: Date.now()
      }
    })
    
    console.log('✅ [DEBUG] 用户头像更新成功')
    return { 
      success: true, 
      avatarUrl: uploadResult.fileID,
      message: '头像上传成功' 
    }
  } catch (error) {
    console.error('❌ [DEBUG] 头像上传失败:', error)
    return { 
      success: false, 
      message: '头像上传失败: ' + error.message 
    }
  }
}