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
    }
  },

  // 组件的初始数据
  data: {
    currentAudio: null, // 当前播放的音频实例
    playingIndex: -1    // 当前播放的单词索引
  },

  // 组件的方法列表
  methods: {
    // 单词点击事件 - 现在也处理音频播放
    onWordTap(e) {
      const { word, index } = e.currentTarget.dataset;
      
      // 如果单词有音频，先播放音频
      if (word && word.audioUrl) {
        this.playAudio(parseInt(index), word.audioUrl);
      }
      
      // 触发原有的单词点击事件
      this.triggerEvent('wordtap', { word, index });
    },

    // 遮罩切换事件
    onToggleMask(e) {
      const { index } = e.currentTarget.dataset;
      const indexNum = parseInt(index);
      
      // 切换当前单词的展开状态
      const words = this.data.words.map((word, i) => {
        if (i === indexNum) {
          return { ...word, isExpanded: !word.isExpanded };
        }
        return word;
      });
      
      // 更新组件内的words数据
      this.setData({ words });
      
      // 通知父组件状态已切换
      this.triggerEvent('maskToggle', { index: indexNum, words });
    },

    // 处理逾期单词
    onHandleOverdue(e) {
      const { index, action } = e.currentTarget.dataset;
      this.triggerEvent('overdueHandle', { index, action });
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
      
      // 设置播放状态
      this.setData({ 
        currentAudio: audio,
        playingIndex: indexNum 
      });
      this.updateWordPlayingState(indexNum);
      
      // 播放结束事件
      audio.onEnded(() => {
        this.setData({ 
          playingIndex: -1,
          currentAudio: null
        });
        this.updateWordPlayingState(-1);
        audio.destroy();
      });
      
      // 播放错误事件
      audio.onError((error) => {
        console.error('音频播放失败:', error);
        wx.showToast({
          title: '音频播放失败',
          icon: 'none',
          duration: 2000
        });
        this.setData({ 
          playingIndex: -1,
          currentAudio: null
        });
        this.updateWordPlayingState(-1);
        audio.destroy();
      });
      
      // 开始播放
      audio.play();
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