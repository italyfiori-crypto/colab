// 设置工具类 - 统一管理用户设置
const SETTINGS_KEY = 'userSettings';
const USER_INFO_KEY = 'userCompleteInfo';
const CACHE_DURATION = 24 * 60 * 60 * 1000; // 24小时缓存时间

// 移除硬编码默认值，所有数据都从云端获取

/**
 * 获取完整用户信息（优先本地缓存）
 * @param {boolean} forceRefresh - 是否强制从云端刷新
 * @returns {Promise<Object>} 完整的用户信息对象
 */
function getCompleteUserInfo(forceRefresh = false) {
  console.log('🔍 [DEBUG] 开始获取完整用户信息');

  // 1. 检查本地缓存（除非强制刷新）
  if (!forceRefresh) {
    const cachedInfo = getCachedUserInfo();
    if (cachedInfo && !isCacheExpired(cachedInfo)) {
      console.log('💾 [DEBUG] 使用本地缓存数据');
      return Promise.resolve(cachedInfo);
    }
  } else {
    console.log('🔄 [DEBUG] 强制刷新，跳过缓存检查');
  }

  // 2. 从云端获取（包含自动创建逻辑）
  console.log('☁️ [DEBUG] 从云端获取用户信息');
  return getUserInfoFromCloud()
    .then(cloudInfo => {
      // 3. 更新本地缓存
      if (cloudInfo) {
        console.log('✅ [DEBUG] 云端数据获取成功，更新本地缓存');
        cacheUserInfo(cloudInfo);
        return cloudInfo;
      }

      // 4. 云端没有返回数据，抛出错误
      console.log('❌ [DEBUG] 云端没有返回数据');
      throw new Error('获取用户信息失败：云端无数据');
    })
    .catch(error => {
      console.error('❌ [DEBUG] 获取用户信息失败:', error);
      // 降级策略：使用缓存，如果缓存也没有则抛出错误
      const cachedInfo = getCachedUserInfo();
      if (cachedInfo) {
        console.log('⚠️ [DEBUG] 使用缓存作为降级方案');
        return cachedInfo;
      }
      throw new Error('获取用户信息失败：' + error.message);
    });
}

/**
 * 从云端获取用户信息
 */
function getUserInfoFromCloud() {
  return wx.cloud.callFunction({
    name: 'userManager',
    data: { action: 'getUserInfo' }
  }).then(result => {
    if (result.result.success) {
      console.log('☁️ [DEBUG] 云端获取成功:', result.result.data);
      return result.result.data;
    } else {
      console.error('❌ [DEBUG] 云端获取失败:', result.result.message);
      throw new Error(result.result.message);
    }
  }).catch(error => {
    console.error('❌ [DEBUG] 云函数调用失败:', error);
    throw error;
  });
}

/**
 * 检查缓存是否过期
 */
function isCacheExpired(cachedData) {
  if (!cachedData.cachedAt) {
    console.log('⏰ [DEBUG] 缓存无时间戳，视为过期');
    return true;
  }
  const isExpired = (Date.now() - cachedData.cachedAt) > CACHE_DURATION;
  console.log('⏰ [DEBUG] 缓存检查:', {
    缓存时间: new Date(cachedData.cachedAt).toLocaleString(),
    是否过期: isExpired
  });
  return isExpired;
}

/**
 * 缓存用户信息
 */
function cacheUserInfo(userInfo) {
  try {
    const cacheData = {
      ...userInfo,
      cachedAt: Date.now()
    };
    wx.setStorageSync(USER_INFO_KEY, cacheData);
    console.log('💾 [DEBUG] 用户信息已缓存');
  } catch (error) {
    console.error('❌ [DEBUG] 缓存用户信息失败:', error);
  }
}

/**
 * 获取缓存的用户信息
 */
function getCachedUserInfo() {
  try {
    const cached = wx.getStorageSync(USER_INFO_KEY);
    if (cached) {
      console.log('📋 [DEBUG] 获取到缓存数据');
      return cached;
    }
    return null;
  } catch (error) {
    console.error('❌ [DEBUG] 获取缓存失败:', error);
    return null;
  }
}


/**
 * 保存完整用户信息并同步到云端
 */
function saveCompleteUserInfo(userInfo) {
  console.log('💾 [DEBUG] 保存完整用户信息:', userInfo);

  // 使用统一的用户信息更新接口
  return wx.cloud.callFunction({
    name: 'userManager',
    data: {
      action: 'updateUserInfo',
      userInfo: {
        nickname: userInfo.nickname,
        avatar_url: userInfo.avatar_url,
        reading_settings: userInfo.reading_settings,
        learning_settings: userInfo.learning_settings
      }
    }
  }).then(result => {
    if (result.result.success) {
      console.log('✅ [DEBUG] 用户信息同步到云端成功');

      // 云端同步成功后，清除缓存并更新新缓存
      clearUserCache();
      cacheUserInfo(userInfo);
      console.log('💾 [DEBUG] 缓存已更新');

      return true;
    } else {
      console.error('❌ [DEBUG] 同步到云端失败:', result.result.message);
      return false;
    }
  }).catch(error => {
    console.error('❌ [DEBUG] 保存用户信息失败:', error);
    return false;
  });
}

/**
 * 更新用户基础信息（昵称、头像）
 */
function updateUserProfile(profileData) {
  console.log('👤 [DEBUG] 更新用户基础信息:', profileData);

  return wx.cloud.callFunction({
    name: 'userManager',
    data: {
      action: 'updateUserProfile',
      profileData: profileData
    }
  }).then(result => {
    if (result.result.success) {
      console.log('✅ [DEBUG] 用户基础信息更新成功');

      // 清除缓存，下次获取时会从云端重新获取最新数据
      clearUserCache();
      console.log('💾 [DEBUG] 已清除缓存，下次将从云端获取最新数据');

      return { success: true };
    } else {
      console.error('❌ [DEBUG] 用户基础信息更新失败:', result.result.message);
      return { success: false, message: result.result.message };
    }
  }).catch(error => {
    console.error('❌ [DEBUG] 更新用户基础信息失败:', error);
    return { success: false, message: error.message };
  });
}

/**
 * 清除用户缓存（用于强制刷新）
 */
function clearUserCache() {
  try {
    wx.removeStorageSync(USER_INFO_KEY);
    console.log('🗑️ [DEBUG] 用户缓存已清除');
  } catch (error) {
    console.error('❌ [DEBUG] 清除缓存失败:', error);
  }
}


/**
 * 字幕语言映射到播放器模式
 * @param {string} subtitleLang - 设置中的字幕语言
 * @returns {string} 播放器需要的模式
 */
function mapSubtitleLangToMode(subtitleLang) {
  const mapping = {
    '中英双语': 'both',
    '仅英文': 'en',
    '仅中文': 'zh'
  };
  return mapping[subtitleLang] || 'both';
}

/**
 * 复习排序方式映射到数据库排序
 * @param {string} reviewSortOrder - 设置中的排序方式
 * @returns {string} 数据库排序方式
 */
function mapReviewSortOrder(reviewSortOrder) {
  const mapping = {
    '优先新词': 'asc',    // 按updated_at升序，先显示较早更新的（新词）
    '优先老词': 'desc'    // 按updated_at降序，先显示较晚更新的（老词）
  };
  return mapping[reviewSortOrder] || 'asc';
}

/**
 * 新学单词排序方式映射到数据库排序
 * @param {string} newWordSort - 设置中的排序方式
 * @returns {string} 数据库排序方式
 */
function mapNewWordSortOrder(newWordSort) {
  const mapping = {
    '优先新词': 'asc',    // 按created_at升序，先显示较早创建的（新词）
    '优先旧词': 'desc'    // 按created_at降序，先显示较晚创建的（旧词）
  };
  return mapping[newWordSort] || 'asc';
}

/**
 * 选择头像图片
 * @returns {Promise} 选择结果
 */
function chooseAvatar() {
  return new Promise((resolve, reject) => {
    wx.chooseImage({
      count: 1,
      sizeType: ['compressed'],
      sourceType: ['album', 'camera'],
      success: (res) => {
        const tempFilePath = res.tempFilePaths[0];
        resolve(tempFilePath);
      },
      fail: reject
    });
  });
}

/**
 * 上传头像到云存储
 * @param {string} tempFilePath - 临时文件路径
 * @returns {Promise} 上传结果
 */
function uploadAvatar(tempFilePath) {
  console.log('📤 [DEBUG] 开始上传头像');

  // 读取文件内容
  const fileManager = wx.getFileSystemManager();
  const fileContent = fileManager.readFileSync(tempFilePath, 'base64');

  // 调用云函数上传
  return wx.cloud.callFunction({
    name: 'userManager',
    data: {
      action: 'uploadAvatar',
      fileContent: fileContent,
      fileName: `avatar_${Date.now()}.jpg`
    }
  }).then(result => {
    if (result.result.success) {
      console.log('✅ [DEBUG] 头像上传成功');
      return {
        success: true,
        avatarUrl: result.result.avatarUrl
      };
    } else {
      console.error('❌ [DEBUG] 头像上传失败:', result.result.message);
      return {
        success: false,
        message: result.result.message
      };
    }
  }).catch(error => {
    console.error('❌ [DEBUG] 头像上传异常:', error);
    return {
      success: false,
      message: '头像上传失败'
    };
  });
}

/**
 * 语音类型映射到音频URL优先级
 * @param {string} voiceType - 设置中的语音类型
 * @returns {Object} 音频URL优先级配置
 */
function mapVoiceTypeToPriority(voiceType) {
  if (voiceType === '美式发音') {
    return {
      primary: 'audio_url_us',
      secondary: 'audio_url',
      fallback: 'audio_url_uk'
    };
  } else if (voiceType === '英式发音') {
    return {
      primary: 'audio_url_uk',
      secondary: 'audio_url',
      fallback: 'audio_url_us'
    };
  }
  // 默认美式发音
  return {
    primary: 'audio_url_us',
    secondary: 'audio_url',
    fallback: 'audio_url_uk'
  };
}


/**
 * 获取云存储文件的临时访问链接
 * @param {string|Array} fileList - 文件ID或文件ID数组
 * @returns {Promise} 临时链接结果
 */
function getTempFileURL(fileList) {
  const files = Array.isArray(fileList) ? fileList : [fileList];
  const validFiles = files.filter(fileId => fileId && typeof fileId === 'string' && fileId.startsWith('cloud://'));

  if (validFiles.length === 0) {
    return Promise.resolve({ fileList: [] });
  }

  return wx.cloud.getTempFileURL({
    fileList: validFiles.map(fileId => ({
      fileID: fileId,
      maxAge: 86400 // 24小时有效期
    }))
  }).then(res => {
    console.log('✅ [DEBUG] 获取临时链接成功:', res.fileList.length, '个文件');
    return res;
  }).catch(error => {
    console.error('❌ [DEBUG] 获取临时链接失败:', error);
    return { fileList: [] };
  });
}

/**
 * 获取单个图片的临时链接
 * @param {string} fileId - 云存储文件ID
 * @returns {Promise<string>} 临时链接URL
 */
function getSingleTempFileURL(fileId) {
  if (!fileId || typeof fileId !== 'string') {
    return Promise.resolve('');
  }

  // 如果不是云存储文件ID，直接返回
  if (!fileId.startsWith('cloud://')) {
    return Promise.resolve(fileId);
  }

  return getTempFileURL([fileId]).then(res => {
    if (res.fileList && res.fileList.length > 0) {
      return res.fileList[0].tempFileURL || '';
    }
    return '';
  });
}

/**
 * 处理图片加载错误的降级方案
 * @param {string} originalUrl - 原始图片URL
 * @returns {string} 代理图片URL
 */
function getProxyImageUrl(originalUrl) {
  if (!originalUrl) return '';

  // 如果已经是代理URL，直接返回
  if (originalUrl.includes('images.weserv.nl')) {
    return originalUrl;
  }

  // 使用图片代理服务绕过防盗链
  return `https://images.weserv.nl/?url=${encodeURIComponent(originalUrl)}`;
}

/**
 * 清除所有设置（重置为默认值）
 */
function clearUserSettings() {
  try {
    wx.removeStorageSync(SETTINGS_KEY);
    console.log('设置已重置');
    return true;
  } catch (error) {
    console.error('重置设置失败:', error);
    return false;
  }
}

module.exports = {
  // 完整用户信息方法
  getCompleteUserInfo,
  saveCompleteUserInfo,
  updateUserProfile,
  clearUserCache,

  // 头像相关方法
  chooseAvatar,
  uploadAvatar,

  // 图片处理方法
  getTempFileURL,
  getSingleTempFileURL,
  getProxyImageUrl,

  // 映射和工具方法
  mapSubtitleLangToMode,
  mapReviewSortOrder,
  mapNewWordSortOrder,
  mapVoiceTypeToPriority,
  clearUserSettings
};