// 设置页面逻辑
const settingsUtils = require('../../utils/settingsUtils.js');

Page({
  data: {
    userInfo: {},
    readingSettings: {},
    learningSettings: {},
    membershipInfo: {
      is_premium: false,
      expire_time: null,
      days_remaining: 0,
      expire_date_str: '',
      status: 'free'
    },
    loading: true,
    // 会员码相关
    showMembershipModal: false,
    codeInput: '',
    activating: false
  },

  async onLoad() {
    wx.setNavigationBarTitle({
      title: '设置'
    });
    await this.loadCompleteUserInfo();
    await this.loadMembershipInfo();
  },

  async onShow() {
    // 页面显示时检查是否需要刷新缓存
    await this.loadCompleteUserInfo();
  },

  /**
   * 加载完整用户信息（使用缓存优先策略）
   */
  async loadCompleteUserInfo(forceRefresh = false) {
    try {
      this.setData({ loading: true });

      console.log('🔄 [DEBUG] 设置页开始加载完整用户信息');

      // 获取用户信息（支持强制刷新）
      const completeInfo = await settingsUtils.getCompleteUserInfo(forceRefresh);

      console.log('✅ [DEBUG] 获取到完整用户信息:', completeInfo);

      // 直接使用云端返回的头像URL（云端已处理临时链接）
      this.setData({
        userInfo: {
          userId: completeInfo.user_id,
          nickName: completeInfo.nickname,
          avatarUrl: completeInfo.avatar_url
        },
        readingSettings: {
          subtitleLang: completeInfo.reading_settings?.subtitle_lang,
          playbackSpeed: completeInfo.reading_settings?.playback_speed
        },
        learningSettings: {
          voiceType: completeInfo.learning_settings?.voice_type,
          dailyWordLimit: completeInfo.learning_settings?.daily_word_limit,
          newWordSort: completeInfo.learning_settings?.new_word_sort
        },
        loading: false
      });

      console.log('✅ [DEBUG] 设置页用户信息加载完成');

    } catch (error) {
      console.error('❌ [DEBUG] 加载用户信息失败:', error);
      wx.showToast({
        title: '加载用户信息失败，请检查网络',
        icon: 'none',
        duration: 3000
      });
      this.setData({ loading: false });

      // 如果是网络问题，建议用户重试
      setTimeout(() => {
        wx.showModal({
          title: '获取用户信息失败',
          content: '无法从服务器获取您的设置信息，请检查网络连接后重试。',
          showCancel: true,
          cancelText: '稍后重试',
          confirmText: '立即重试',
          success: (res) => {
            if (res.confirm) {
              this.loadCompleteUserInfo();
            }
          }
        });
      }, 1000);
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
        reading_settings: {
          subtitle_lang: this.data.readingSettings.subtitleLang,
          playback_speed: this.data.readingSettings.playbackSpeed
        },
        learning_settings: {
          voice_type: this.data.learningSettings.voiceType,
          daily_word_limit: this.data.learningSettings.dailyWordLimit,
          new_word_sort: this.data.learningSettings.newWordSort
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

      // 强制从云端获取最新数据
      await this.loadCompleteUserInfo(true);

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

  // 选择新学单词排序
  onSelectNewWordSort() {
    const options = ['优先新词', '优先旧词'];
    const current = this.data.learningSettings?.newWordSort || '优先新词';
    const currentIndex = options.indexOf(current);

    wx.showActionSheet({
      itemList: options,
      success: (res) => {
        if (res.tapIndex !== currentIndex) {
          this.setData({
            'learningSettings.newWordSort': options[res.tapIndex]
          });
          this.saveCurrentSettings();

          // 提示用户设置已生效
          wx.showToast({
            title: `已设置为${options[res.tapIndex]}`,
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
      console.log("uploadResult:", uploadResult)
      if (uploadResult.success) {
        // 更新页面显示
        this.setData({
          'userInfo.avatarUrl': uploadResult.avatarUrl
        });

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
      content: `${currentNickname}`,
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

            // 保存到云端 - 使用专门的用户信息更新方法
            const updateResult = await settingsUtils.updateUserProfile({
              nickname: newNickname
            });

            if (updateResult.success) {
              wx.showToast({
                title: '昵称更新成功',
                icon: 'success'
              });
            } else {
              // 如果更新失败，恢复原来的昵称
              this.setData({
                'userInfo.nickName': currentNickname
              });
              wx.showToast({
                title: updateResult.message || '昵称更新失败',
                icon: 'none'
              });
            }
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

  // 头像加载错误处理
  onAvatarLoadError(e) {
    console.error('❌ [DEBUG] 头像加载失败:', e.detail);

    const currentUrl = this.data.userInfo.avatarUrl;
    console.log('🔄 [DEBUG] 尝试使用代理服务加载头像:', currentUrl);

    // 如果不是默认头像且未使用代理，尝试使用代理服务
    if (currentUrl &&
      !currentUrl.includes('/resource/icons/avatar.svg') &&
      !currentUrl.includes('images.weserv.nl')) {

      const proxyUrl = settingsUtils.getProxyImageUrl(currentUrl);
      console.log('🔄 [DEBUG] 使用代理URL:', proxyUrl);

      this.setData({
        'userInfo.avatarUrl': proxyUrl
      });
    } else {
      // 最终降级为默认头像
      console.log('⚠️ [DEBUG] 使用默认头像');
      this.setData({
        'userInfo.avatarUrl': '/resource/icons/avatar.svg'
      });
    }
  },

  /**
   * 加载会员信息
   */
  async loadMembershipInfo() {
    try {
      console.log('🔄 [DEBUG] 开始加载会员信息');

      const result = await wx.cloud.callFunction({
        name: 'membershipManager',
        data: { action: 'checkMembership' }
      });

      if (result.result.success) {
        const membershipData = result.result.data;
        console.log('✅ [DEBUG] 会员信息加载成功:', membershipData);

        // 计算到期日期字符串和会员状态
        let expireDateStr = ''
        let membershipStatus = 'free' // free, active, expired

        if (membershipData.expire_time) {
          const expireDate = new Date(membershipData.expire_time)
          expireDateStr = `${expireDate.getFullYear()}年${expireDate.getMonth() + 1}月${expireDate.getDate()}日`

          if (membershipData.is_premium) {
            membershipStatus = 'active'
          } else {
            membershipStatus = 'expired'
          }
        }

        this.setData({
          membershipInfo: {
            is_premium: membershipData.is_premium,
            expire_time: membershipData.expire_time,
            days_remaining: membershipData.days_remaining,
            expire_date_str: expireDateStr,
            status: membershipStatus
          }
        });
      } else {
        console.error('❌ [DEBUG] 加载会员信息失败:', result.result.message);
      }
    } catch (error) {
      console.error('❌ [DEBUG] 会员信息请求异常:', error);
    }
  },

  /**
   * 点击会员操作按钮
   */
  onMembershipAction() {
    this.setData({
      showMembershipModal: true,
      codeInput: ''
    });
  },

  /**
   * 关闭会员码输入弹窗
   */
  onCloseMembershipModal() {
    this.setData({
      showMembershipModal: false,
      codeInput: '',
      activating: false
    });
  },

  /**
   * 会员码输入
   */
  onCodeInput(e) {
    const value = e.detail.value.toUpperCase();
    this.setData({
      codeInput: value
    });
  },

  /**
   * 激活会员码
   */
  async onActivateCode() {
    if (!this.data.codeInput || this.data.codeInput.length !== 12) {
      wx.showToast({
        title: '请输入12位激活码',
        icon: 'none'
      });
      return;
    }

    this.setData({ activating: true });

    try {
      console.log('🔄 [DEBUG] 开始激活会员码:', this.data.codeInput);

      const result = await wx.cloud.callFunction({
        name: 'membershipManager',
        data: {
          action: 'activateCode',
          code: this.data.codeInput
        }
      });

      if (result.result.success) {
        // 激活成功
        console.log('✅ [DEBUG] 会员码激活成功:', result.result);

        wx.showToast({
          title: '解锁成功！',
          icon: 'success'
        });

        // 关闭弹窗
        this.setData({
          showMembershipModal: false,
          codeInput: ''
        });

        // 重新加载会员信息
        await this.loadMembershipInfo();

      } else {
        // 激活失败
        console.error('❌ [DEBUG] 会员码激活失败:', result.result.message);
        wx.showToast({
          title: result.result.message,
          icon: 'none',
          duration: 3000
        });
      }
    } catch (error) {
      console.error('❌ [DEBUG] 激活会员码请求异常:', error);
      wx.showToast({
        title: '网络错误，请稍后重试',
        icon: 'none'
      });
    } finally {
      this.setData({ activating: false });
    }
  },

});