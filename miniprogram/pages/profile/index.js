// 设置页面逻辑
const settingsUtils = require('../../utils/settingsUtils.js');

Page({
  data: {
    userInfo: {},
    readingSettings: {},
    learningSettings: {},
    loading: true
  },

  async onLoad() {
    wx.setNavigationBarTitle({
      title: '设置'
    });
    await this.loadCompleteUserInfo();
  },

  async onShow() {
    // 页面显示时检查是否需要刷新缓存
    await this.loadCompleteUserInfo();
  },

  /**
   * 加载完整用户信息（使用缓存优先策略）
   */
  async loadCompleteUserInfo() {
    try {
      this.setData({ loading: true });
      
      console.log('🔄 [DEBUG] 设置页开始加载完整用户信息');
      
      // 使用新的缓存优先策略
      const completeInfo = await settingsUtils.getCompleteUserInfo();
      
      console.log('✅ [DEBUG] 获取到完整用户信息:', completeInfo);
      
      this.setData({
        userInfo: {
          userId: completeInfo.user_id || 100000,
          nickName: completeInfo.nickname || '学习者',
          avatarUrl: completeInfo.avatar_url || '/resource/icons/avatar.svg'
        },
        readingSettings: {
          subtitleLang: completeInfo.reading_settings?.subtitle_lang || '中英双语',
          playbackSpeed: completeInfo.reading_settings?.playback_speed || 1.0
        },
        learningSettings: {
          voiceType: completeInfo.learning_settings?.voice_type || '美式发音',
          dailyWordLimit: completeInfo.learning_settings?.daily_word_limit || 20
        },
        loading: false
      });
      
      console.log('✅ [DEBUG] 设置页用户信息加载完成');
      
    } catch (error) {
      console.error('❌ [DEBUG] 加载用户信息失败:', error);
      wx.showToast({
        title: '加载失败，使用默认设置',
        icon: 'none'
      });
      this.setData({ loading: false });
    }
  },

  /**
   * 保存当前设置到缓存和云端
   */
  async saveCurrentSettings() {
    try {
      console.log('💾 [DEBUG] 开始保存当前设置');
      
      const completeInfo = {
        user_id: this.data.userInfo.userId,
        nickname: this.data.userInfo.nickName,
        avatar_url: this.data.userInfo.avatarUrl,
        reading_settings: {
          subtitle_lang: this.data.readingSettings.subtitleLang,
          playback_speed: this.data.readingSettings.playbackSpeed
        },
        learning_settings: {
          voice_type: this.data.learningSettings.voiceType,
          daily_word_limit: this.data.learningSettings.dailyWordLimit
        },
        updated_at: Date.now()
      };
      
      const success = await settingsUtils.saveCompleteUserInfo(completeInfo);
      
      if (success) {
        wx.showToast({
          title: '设置已保存',
          icon: 'success'
        });
        console.log('✅ [DEBUG] 设置保存成功');
      } else {
        wx.showToast({
          title: '保存失败，请重试',
          icon: 'none'
        });
        console.error('❌ [DEBUG] 设置保存失败');
      }
    } catch (error) {
      console.error('❌ [DEBUG] 保存设置异常:', error);
      wx.showToast({
        title: '保存异常',
        icon: 'none'
      });
    }
  },

  /**
   * 下拉刷新 - 强制从云端获取最新数据
   */
  async onPullDownRefresh() {
    try {
      console.log('🔄 [DEBUG] 用户触发下拉刷新');
      
      // 清除缓存，强制从云端获取
      settingsUtils.clearUserCache();
      await this.loadCompleteUserInfo();
      
      wx.showToast({
        title: '刷新成功',
        icon: 'success'
      });
      
      console.log('✅ [DEBUG] 下拉刷新完成');
    } catch (error) {
      console.error('❌ [DEBUG] 下拉刷新失败:', error);
      wx.showToast({
        title: '刷新失败',
        icon: 'none'
      });
    } finally {
      wx.stopPullDownRefresh();
    }
  },


  // 选择字幕语言
  onSelectSubtitleLang() {
    const options = ['中英双语', '仅英文', '仅中文'];
    const current = this.data.readingSettings.subtitleLang;
    const currentIndex = options.indexOf(current);

    wx.showActionSheet({
      itemList: options,
      success: (res) => {
        if (res.tapIndex !== currentIndex) {
          this.setData({
            'readingSettings.subtitleLang': options[res.tapIndex]
          });
          this.saveCurrentSettings();
        }
      }
    });
  },

  // 选择播放速度
  onSelectPlaybackSpeed() {
    const options = ['0.8x', '0.9x', '1.0x', '1.1x', '1.2x', '1.3x'];
    const speeds = [0.8, 0.9, 1.0, 1.1, 1.2, 1.3];
    const current = this.data.readingSettings?.playbackSpeed || 1.0;
    const currentIndex = speeds.indexOf(current);

    wx.showActionSheet({
      itemList: options,
      success: (res) => {
        if (res.tapIndex !== currentIndex) {
          this.setData({
            'readingSettings.playbackSpeed': speeds[res.tapIndex]
          });
          this.saveCurrentSettings();
        }
      }
    });
  },


  // 选择语音类型
  onSelectVoiceType() {
    const options = ['美式发音', '英式发音'];
    const current = this.data.learningSettings.voiceType;
    const currentIndex = options.indexOf(current);

    wx.showActionSheet({
      itemList: options,
      success: (res) => {
        if (res.tapIndex !== currentIndex) {
          this.setData({
            'learningSettings.voiceType': options[res.tapIndex]
          });
          this.saveCurrentSettings();
        }
      }
    });
  },

  // 设置每日单词上限
  onSetDailyWordLimit() {
    const options = ['10个', '20个', '30个', '50个', '80个', '100个'];
    const limits = [10, 20, 30, 50, 80, 100];
    const current = this.data.learningSettings?.dailyWordLimit || 20;
    const currentIndex = limits.indexOf(current);

    wx.showActionSheet({
      itemList: options,
      success: (res) => {
        if (res.tapIndex !== currentIndex) {
          this.setData({
            'learningSettings.dailyWordLimit': limits[res.tapIndex]
          });
          this.saveCurrentSettings();
          
          // 提示用户设置已生效
          wx.showToast({
            title: `已设置为${limits[res.tapIndex]}个/天`,
            icon: 'success'
          });
        }
      }
    });
  },

  // 编辑头像
  async onEditAvatar() {
    try {
      wx.showLoading({ title: '上传中...' });
      
      const tempFilePath = await settingsUtils.chooseAvatar();
      const uploadResult = await settingsUtils.uploadAvatar(tempFilePath);
      
      if (uploadResult.success) {
        // 更新页面显示
        this.setData({
          'userInfo.avatarUrl': uploadResult.avatarUrl
        });
        
        // 保存到云端
        await this.saveCurrentSettings();
        
        wx.showToast({
          title: '头像更新成功',
          icon: 'success'
        });
      } else {
        wx.showToast({
          title: uploadResult.message || '上传失败',
          icon: 'none'
        });
      }
    } catch (error) {
      console.error('头像编辑失败:', error);
      wx.showToast({
        title: '操作已取消',
        icon: 'none'
      });
    } finally {
      wx.hideLoading();
    }
  },

  // 编辑昵称
  onEditNickname() {
    const currentNickname = this.data.userInfo.nickName;
    
    wx.showModal({
      title: '修改昵称',
      content: `当前昵称：${currentNickname}`,
      placeholderText: '请输入新昵称',
      editable: true,
      success: async (res) => {
        if (res.confirm && res.content) {
          const newNickname = res.content.trim();
          
          if (newNickname.length > 20) {
            wx.showToast({
              title: '昵称不能超过20个字符',
              icon: 'none'
            });
            return;
          }
          
          if (newNickname !== currentNickname) {
            // 更新页面显示
            this.setData({
              'userInfo.nickName': newNickname
            });
            
            // 保存到云端
            await this.saveCurrentSettings();
            
            wx.showToast({
              title: '昵称更新成功',
              icon: 'success'
            });
          }
        }
      }
    });
  },

  // 显示帮助
  onShowHelp() {
    wx.showModal({
      title: '使用帮助',
      content: '1. 每日学习：建议坚持每天学习新单词\n2. 及时复习：按时复习逾期单词\n3. 合理设置：根据自己的时间调整学习目标\n4. 循序渐进：从简单单词开始，逐步提升难度',
      showCancel: false,
      confirmText: '知道了'
    });
  },

  // 意见反馈
  onFeedback() {
    wx.showModal({
      title: '意见反馈',
      content: '感谢您的使用！如有问题或建议，请联系开发者微信: yusir2024',
      showCancel: false,
      confirmText: '好的'
    });
  },

});