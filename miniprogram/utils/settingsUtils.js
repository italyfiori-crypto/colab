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
async function getCompleteUserInfo(forceRefresh = false) {
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
 * 更新用户基础信息（昵称、头像）- 使用统一的updateUserInfo接口
 */
function updateUserProfile(profileData) {
  console.log('👤 [DEBUG] 更新用户基础信息:', profileData);

  return wx.cloud.callFunction({
    name: 'userManager',
    data: {
      action: 'updateUserInfo',
      userInfo: {
        nickname: profileData.nickname,
        avatar_url: profileData.avatar_url
      }
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
      success: async (res) => {
        const originalPath = res.tempFilePaths[0];
        console.log('📸 [DEBUG] 选择图片成功:', originalPath);

        try {
          // 获取文件信息
          const fileManager = wx.getFileSystemManager();
          const fileStats = fileManager.statSync(originalPath);
          console.log('📋 [DEBUG] 原始图片信息:', {
            路径: originalPath,
            大小: fileStats.size,
            大小MB: (fileStats.size / 1024 / 1024).toFixed(2)
          });

          // 如果文件小于500KB，直接使用
          if (fileStats.size < 200 * 1024) {
            console.log('✅ [DEBUG] 图片大小合适，直接使用');
            resolve(originalPath);
            return;
          }

          // 大图片需要压缩
          console.log('🔄 [DEBUG] 开始压缩图片...');
          wx.compressImage({
            src: originalPath,
            quality: 70, // 压缩质量
            success: (compressRes) => {
              console.log('✅ [DEBUG] 图片压缩成功:', compressRes.tempFilePath);

              // 检查压缩后大小
              try {
                const compressedStats = fileManager.statSync(compressRes.tempFilePath);
                console.log('📊 [DEBUG] 压缩后图片信息:', {
                  路径: compressRes.tempFilePath,
                  大小: compressedStats.size,
                  大小MB: (compressedStats.size / 1024 / 1024).toFixed(2),
                  压缩比: ((fileStats.size - compressedStats.size) / fileStats.size * 100).toFixed(1) + '%'
                });

                resolve(compressRes.tempFilePath);
              } catch (statError) {
                console.warn('⚠️ [DEBUG] 获取压缩后文件信息失败，使用压缩文件:', statError);
                resolve(compressRes.tempFilePath);
              }
            },
            fail: (compressError) => {
              console.warn('⚠️ [DEBUG] 图片压缩失败，使用原图:', compressError);
              // 压缩失败时使用原图（可能在某些设备上发生）
              resolve(originalPath);
            }
          });

        } catch (error) {
          console.warn('⚠️ [DEBUG] 处理图片时出错，使用原图:', error);
          resolve(originalPath);
        }
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
function uploadAvatar(tempFilePath, retryCount = 0) {
  console.log('📤 [DEBUG] 开始上传头像，文件路径:', tempFilePath, '重试次数:', retryCount);

  return new Promise(async (resolve, reject) => {
    // 验证文件路径
    if (!tempFilePath || typeof tempFilePath !== 'string') {
      console.error('❌ [DEBUG] 文件路径无效:', tempFilePath);
      resolve({
        success: false,
        message: '文件路径无效'
      });
      return;
    }

    // 获取用户ID用于生成文件路径
    let userId = 'anonymous';
    try {
      const userInfo = await getCompleteUserInfo();
      userId = userInfo.user_id || 'anonymous';
    } catch (error) {
      console.warn('⚠️ [DEBUG] 获取用户ID失败，使用匿名用户:', error);
    }
    
    const timestamp = Date.now();
    const cloudPath = `avatars/${userId}_${timestamp}.jpg`;

    console.log('☁️ [DEBUG] 准备上传到云存储:', {
      本地路径: tempFilePath,
      云存储路径: cloudPath
    });

    // 直接上传到云存储
    wx.cloud.uploadFile({
      cloudPath: cloudPath,
      filePath: tempFilePath,
      success: async (uploadResult) => {
        console.log('✅ [DEBUG] 云存储上传成功:', {
          fileID: uploadResult.fileID,
          statusCode: uploadResult.statusCode
        });

        try {
          // 调用云函数更新用户头像信息
          const updateResult = await wx.cloud.callFunction({
            name: 'userManager',
            data: {
              action: 'updateAvatar',
              fileID: uploadResult.fileID
            },
            timeout: 10000 // 10秒超时
          });

          console.log('☁️ [DEBUG] 云函数更新头像信息:', updateResult.result);

          if (updateResult.result && updateResult.result.success) {
            resolve({
              success: true,
              avatarUrl: updateResult.result.avatarUrl || uploadResult.fileID
            });
          } else {
            const errorMsg = updateResult.result ? updateResult.result.message : '更新用户信息失败';
            console.error('❌ [DEBUG] 更新头像信息失败:', errorMsg);

            // 更新失败时，清理已上传的文件
            try {
              await wx.cloud.deleteFile({
                fileList: [uploadResult.fileID]
              });
              console.log('🗑️ [DEBUG] 已清理失败的上传文件');
            } catch (deleteError) {
              console.warn('⚠️ [DEBUG] 清理文件失败:', deleteError);
            }

            resolve({
              success: false,
              message: errorMsg
            });
          }
        } catch (updateError) {
          console.error('❌ [DEBUG] 调用云函数更新头像失败:', updateError);

          // 清理已上传的文件
          try {
            await wx.cloud.deleteFile({
              fileList: [uploadResult.fileID]
            });
            console.log('🗑️ [DEBUG] 已清理失败的上传文件');
          } catch (deleteError) {
            console.warn('⚠️ [DEBUG] 清理文件失败:', deleteError);
          }

          // 重试逻辑
          if (retryCount < 2) {
            console.log('🔄 [DEBUG] 准备重试上传，重试次数:', retryCount + 1);
            setTimeout(() => {
              uploadAvatar(tempFilePath, retryCount + 1).then(resolve).catch(reject);
            }, 1000 * (retryCount + 1));
          } else {
            resolve({
              success: false,
              message: '更新头像信息失败: ' + updateError.message
            });
          }
        }
      },
      fail: (uploadError) => {
        console.error('❌ [DEBUG] 云存储上传失败:', uploadError);

        // 重试逻辑
        if (retryCount < 2 && shouldRetryUpload(uploadError)) {
          console.log('🔄 [DEBUG] 准备重试上传，重试次数:', retryCount + 1);
          setTimeout(() => {
            uploadAvatar(tempFilePath, retryCount + 1).then(resolve).catch(reject);
          }, 1000 * (retryCount + 1));
        } else {
          resolve({
            success: false,
            message: '上传失败: ' + (uploadError.errMsg || '网络异常')
          });
        }
      }
    });
  });
}

/**
 * 判断是否应该重试上传
 * @param {Object} error - 错误对象或结果对象
 * @returns {boolean} 是否应该重试
 */
function shouldRetryUpload(error) {
  if (!error) return false;

  // 检查错误消息中是否包含可重试的错误
  const retryableErrors = [
    'empty poll result',
    'timeout',
    'network error',
    'connection',
    '404006',
    '网络异常',
    '超时',
    '连接失败'
  ];

  const errorMessage = (error.message || error.errMsg || '').toLowerCase();
  const shouldRetry = retryableErrors.some(retryableError =>
    errorMessage.includes(retryableError.toLowerCase())
  );

  console.log('🤔 [DEBUG] 判断是否重试:', {
    错误信息: errorMessage,
    应该重试: shouldRetry,
    错误码: error.code
  });

  return shouldRetry;
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