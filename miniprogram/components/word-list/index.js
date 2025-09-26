// 可复用的单词列表组件
Component({
  // 组件的属性列表
  properties: {
    // 单词列表数据
    words: {
      type: Array,
      value: []
    },
    // 显示模式: full(完整) | readonly(只读，非full时默认为只读)
    mode: {
      type: String,
      value: 'full'
    },
    // 单词类型: new | review | overdue
    wordType: {
      type: String,
      value: 'new'
    },
    // 显示模式: both | chinese-mask | english-mask
    displayMode: {
      type: String,
      value: 'both'
    },
    // 是否显示序号
    showNumber: {
      type: Boolean,
      value: true
    },
    // 自定义样式类
    customClass: {
      type: String,
      value: ''
    },
    // 是否显示收藏按钮
    showFavoriteBtn: {
      type: Boolean,
      value: false
    },
    // 播放速度
    playSpeed: {
      type: Number,
      value: 1.0
    }
  },

  // 组件的初始数据
  data: {
    currentAudio: null, // 当前播放的音频实例
    playingIndex: -1,   // 当前播放的单词索引
    userSettings: {}    // 用户设置
  },

  // 组件生命周期
  attached() {
    // 组件附加到页面时，获取用户设置
    this.getUserSettings();
  },

  // 组件的方法列表
  methods: {
    // 获取用户设置
    async getUserSettings() {
      try {
        const settingsUtils = require('../../utils/settingsUtils.js');
        const userInfo = await settingsUtils.getCompleteUserInfo();
        this.setData({ userSettings: userInfo });
      } catch (error) {
        console.error('获取用户设置失败:', error);
      }
    },

    // 根据用户设置选择音频和音标
    getAudioAndPhonetic(word) {
      const { userSettings } = this.data;
      const voiceType = userSettings.learning_settings?.voice_type || '美式发音';
      
      if (voiceType === '美式发音') {
        return {
          audioUrl: word.audio_url_us || word.audio_url_uk || '',
          phonetic: word.phonetic_us || word.phonetic_uk || ''
        };
      } else {
        return {
          audioUrl: word.audio_url_uk || word.audio_url_us || '',
          phonetic: word.phonetic_uk || word.phonetic_us || ''
        };
      }
    },

    // 单词点击事件 - 现在也处理音频播放
    onWordTap(e) {
      const { word, index } = e.currentTarget.dataset;
      // 优先使用预处理的audioUrl，否则使用getAudioAndPhonetic方法
      let audioUrl = word.audioUrl;
      if (!audioUrl) {
        const { audioUrl: computedAudioUrl } = this.getAudioAndPhonetic(word);
        audioUrl = computedAudioUrl;
      }
      
      console.log('🔊 [DEBUG] 单词点击事件:', { 
        word: word?.word, 
        index, 
        hasAudio: !!audioUrl,
        audioUrl,
        usingPreprocessed: !!word.audioUrl
      });
      
      // 如果单词有音频，播放音频
      if (audioUrl) {
        console.log('🎵 [DEBUG] 开始播放音频:', audioUrl);
        this.playAudio(parseInt(index), audioUrl);
      } else {
        console.warn('⚠️ [DEBUG] 单词没有音频URL');
      }
      
      // 触发原有的单词点击事件给父组件
      this.triggerEvent('wordtap', { word, index });
    },

    // 遮罩切换事件
    onToggleMask(e) {
      const { index } = e.currentTarget.dataset;
      const indexNum = parseInt(index);
      const word = this.data.words[indexNum];
      // 优先使用预处理的audioUrl，否则使用getAudioAndPhonetic方法
      let audioUrl = word.audioUrl;
      if (!audioUrl) {
        const { audioUrl: computedAudioUrl } = this.getAudioAndPhonetic(word);
        audioUrl = computedAudioUrl;
      }
      
      console.log('🎭 [DEBUG] 遮罩点击事件:', { 
        index: indexNum, 
        word: word?.word,
        hasAudio: !!audioUrl,
        usingPreprocessed: !!word.audioUrl
      });
      
      // 如果单词有音频，播放音频
      if (audioUrl) {
        console.log('🎵 [DEBUG] 遮罩点击播放音频:', audioUrl);
        this.playAudio(indexNum, audioUrl);
      }
      
      // 切换当前单词的展开状态
      const words = this.data.words.map((w, i) => {
        if (i === indexNum) {
          return { ...w, isExpanded: !w.isExpanded };
        }
        return w;
      });
      
      // 更新组件内的words数据
      this.setData({ words });
      
      // 通知父组件状态已切换
      this.triggerEvent('maskToggle', { index: indexNum, words });
    },

    // 处理逾期单词
    async onHandleOverdue(e) {
      const { index, action } = e.currentTarget.dataset;
      
      // 如果是删除操作，直接调用articleDetailData云函数
      if (action === 'delete') {
        const word = this.data.words[index];
        if (!word) {
          console.error('❌ 单词不存在:', index);
          return;
        }
        
        try {
          console.log('🗑️ [DEBUG] 开始删除单词:', word.word);
          
          // 显示确认对话框
          wx.showModal({
            title: '确认删除',
            content: `确定要删除单词 "${word.word}" 吗？此操作不可恢复。`,
            success: async (res) => {
              if (res.confirm) {
                // 调用articleDetailData云函数删除单词
                const result = await wx.cloud.callFunction({
                  name: 'articleDetailData',
                  data: {
                    type: 'removeWordFromCollection',
                    word: word.word,
                    user_id: wx.getStorageSync('userId') || 'default_user'
                  }
                });
                
                if (result.result.code === 0) {
                  console.log('✅ [DEBUG] 单词删除成功:', word.word);
                  wx.showToast({
                    title: '删除成功',
                    icon: 'success'
                  });
                  
                  // 通知父组件移除单词
                  this.triggerEvent('overdueHandle', { index, action: 'delete' });
                } else {
                  console.error('❌ [DEBUG] 单词删除失败:', result.result.message);
                  wx.showToast({
                    title: '删除失败',
                    icon: 'none'
                  });
                }
              }
            }
          });
        } catch (error) {
          console.error('❌ [DEBUG] 删除单词出错:', error);
          wx.showToast({
            title: '删除失败',
            icon: 'none'
          });
        }
      } else {
        // 其他操作（还记得、忘记了）继续走原有逻辑
        this.triggerEvent('overdueHandle', { index, action });
      }
    },

    // 收藏按钮点击事件
    onToggleFavorite(e) {
      const { index } = e.currentTarget.dataset;
      const word = this.data.words[index];
      
      console.log('⭐ [DEBUG] 收藏按钮点击:', {
        word: word.word,
        currentState: word.is_favorited
      });
      
      this.triggerEvent('favoriteToggle', { 
        index: parseInt(index), 
        word,
        currentState: word.is_favorited 
      });
    },

    // 音频播放方法
    playAudio(indexNum, audioUrl) {
      if (!audioUrl) {
        console.warn('音频URL不存在');
        return;
      }
      
      // 如果当前有音频在播放，先停止
      if (this.data.currentAudio) {
        this.data.currentAudio.stop();
        this.data.currentAudio.destroy();
        this.setData({ currentAudio: null });
      }
      
      // 如果点击的是正在播放的单词，停止播放
      if (this.data.playingIndex === indexNum) {
        this.setData({ playingIndex: -1 });
        this.updateWordPlayingState(-1);
        return;
      }
      
      // 创建新的音频实例
      const audio = wx.createInnerAudioContext();
      audio.src = audioUrl;
      // 应用播放速度
      audio.playbackRate = this.properties.playSpeed;
      
      // 设置播放状态
      this.setData({ 
        currentAudio: audio,
        playingIndex: indexNum 
      });
      this.updateWordPlayingState(indexNum);
      
      // 音频准备就绪事件
      audio.onCanplay(() => {
        console.log('🎵 [DEBUG] 音频资源加载完成，开始播放');
        audio.play();
      });
      
      // 播放结束事件
      audio.onEnded(() => {
        console.log('🎵 [DEBUG] 音频播放完成');
        this.setData({ 
          playingIndex: -1,
          currentAudio: null
        });
        this.updateWordPlayingState(-1);
        audio.destroy();
      });
      
      // 播放错误事件 - 静默处理
      audio.onError(() => {
        this.cleanupAudio(audio);
      });
      
      // 简化的超时处理 - 直接尝试播放，失败就清理
      setTimeout(() => {
        if (this.data.playingIndex === indexNum && audio) {
          try {
            // 直接调用play，不检查返回值类型
            const result = audio.play();
            // 如果返回Promise就添加错误处理，否则忽略
            if (result && result.catch) {
              result.catch(() => this.cleanupAudio(audio));
            }
          } catch (err) {
            this.cleanupAudio(audio);
          }
        }
      }, 3000);
    },

    // 简化的音频清理方法
    cleanupAudio(audio = null) {
      // 静默重置播放状态
      this.setData({ 
        playingIndex: -1,
        currentAudio: null
      });
      this.updateWordPlayingState(-1);
      
      // 销毁音频对象
      if (audio && typeof audio.destroy === 'function') {
        try {
          audio.destroy();
        } catch (e) {
          // 静默处理销毁错误
        }
      }
    },

    // 更新单词播放状态
    updateWordPlayingState(playingIndex) {
      const words = this.data.words.map((word, index) => ({
        ...word,
        playing: index === playingIndex
      }));
      this.setData({ words });
    }
  },

  // 组件生命周期
  detached() {
    // 组件销毁时清理音频资源
    if (this.data.currentAudio) {
      this.data.currentAudio.stop();
      this.data.currentAudio.destroy();
      this.setData({ currentAudio: null });
    }
  }
});