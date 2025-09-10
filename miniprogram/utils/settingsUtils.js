// 设置工具类 - 统一管理用户设置
const SETTINGS_KEY = 'userSettings';
const USER_INFO_KEY = 'userCompleteInfo';
const CACHE_DURATION = 24 * 60 * 60 * 1000; // 24小时缓存时间

// 最基本的前端硬编码默认值（仅用于网络异常时的降级）
const FALLBACK_USER_INFO = {
  user_id: 100000,
  nickname: '学习者',
  avatar_url: '/resource/icons/avatar.svg',
  reading_settings: {
    subtitle_lang: '中英双语',
    playback_speed: 1.0
  },
  learning_settings: {
    voice_type: '美式发音',
    daily_word_limit: 20
  },
  created_at: Date.now(),
  updated_at: Date.now()
};

/**
 * 获取完整用户信息（优先本地缓存）
 * @returns {Promise<Object>} 完整的用户信息对象
 */
function getCompleteUserInfo() {
  console.log('🔍 [DEBUG] 开始获取完整用户信息');
  
  // 1. 检查本地缓存
  const cachedInfo = getCachedUserInfo();
  if (cachedInfo && !isCacheExpired(cachedInfo)) {
    console.log('💾 [DEBUG] 使用本地缓存数据');
    return Promise.resolve(cachedInfo);
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
      
      // 4. 降级使用默认设置（这种情况应该很少发生）
      console.log('⚠️ [DEBUG] 云端没有返回数据，使用降级默认值');
      return FALLBACK_USER_INFO;
    })
    .catch(error => {
      console.error('❌ [DEBUG] 获取用户信息失败:', error);
      // 降级策略：使用缓存或最基本的硬编码默认值
      return getCachedUserInfo() || FALLBACK_USER_INFO;
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
  
  // 1. 更新本地缓存
  cacheUserInfo(userInfo);
  
  // 2. 同步到云端
  return wx.cloud.callFunction({
    name: 'userManager',
    data: {
      action: 'updateUserSettings',
      settingsData: {
        reading_settings: userInfo.reading_settings,
        learning_settings: userInfo.learning_settings
      }
    }
  }).then(result => {
    if (result.result.success) {
      console.log('✅ [DEBUG] 设置同步到云端成功');
      return true;
    } else {
      console.error('❌ [DEBUG] 设置同步到云端失败:', result.result.message);
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
      
      // 更新本地缓存
      const cachedInfo = getCachedUserInfo();
      if (cachedInfo) {
        const updatedInfo = { ...cachedInfo };
        if (profileData.nickname) updatedInfo.nickname = profileData.nickname;
        if (profileData.avatar_url) updatedInfo.avatar_url = profileData.avatar_url;
        updatedInfo.updated_at = Date.now();
        cacheUserInfo(updatedInfo);
      }
      
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
 * 根据设置获取单词音频URL
 * @param {Object} word - 单词对象
 * @param {string} voiceType - 语音类型设置
 * @returns {string} 音频URL
 */
function getWordAudioUrl(word, voiceType) {
  const priority = mapVoiceTypeToPriority(voiceType);
  
  return word[priority.primary] || 
         word[priority.secondary] || 
         word[priority.fallback] || '';
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
  
  // 映射和工具方法
  mapSubtitleLangToMode,
  mapReviewSortOrder,
  mapVoiceTypeToPriority,
  getWordAudioUrl,
  clearUserSettings,
  
  // 常量  
  FALLBACK_USER_INFO
};