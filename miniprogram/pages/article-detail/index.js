const articleDetailData = require('../../mock/articleDetailData.js');

Page({
    data: {
        // 文章信息
        articleId: null,
        title: '',

        // 字幕数据
        subtitles: [],
        currentIndex: 0,
        currentSubtitleId: '',
        showChinese: true,
        scrollOffset: 0,
        containerHeight: 0,

        // 音频控制
        isPlaying: false,
        currentTime: 0,
        duration: 240, // 4分钟，与mock音频长度匹配
        playSpeed: 1,
        speedOptions: [0.7, 0.85, 1.0, 1.25],
        isLooping: false, // 循环播放当前字幕

        // UI状态
        showSettings: false,
        isFavorited: false,
        showVocabulary: false,
        
        // 单词卡片数据
        vocabularyTitle: '',
        vocabularyWords: [],

        // UI状态相关的数据，图标现在直接在模板中使用本地文件
    },

    onLoad(options) {
        const articleId = options.id;
        this.setData({ articleId });

        // 设置标题
        wx.setNavigationBarTitle({
            title: '英语学习'
        });

        // 加载字幕数据
        this.loadSubtitleData();

        // 创建音频对象
        this.createAudioContext();

        // 加载收藏状态
        this.loadFavoriteStatus();

        // 获取容器高度
        this.getContainerHeight();
    },

    onUnload() {
        // 清理音频
        if (this.audioContext) {
            this.audioContext.destroy();
        }
        // 清理定时器
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
        }
    },

    // 加载字幕数据
    loadSubtitleData() {
        // 这里应该根据articleId获取对应的数据，现在使用solar.txt
        const mockData = articleDetailData.subtitles;
        const subtitles = this.parseSubtitleData(mockData);
        this.setData({ subtitles });
    },

    // 解析字幕数据
    parseSubtitleData(data) {
        const lines = data.trim().split('\n');
        const subtitles = [];

        for (let i = 0; i < lines.length; i += 3) {
            if (i + 2 < lines.length) {
                const timeText = lines[i];
                const english = lines[i + 1];
                const chinese = lines[i + 2];

                // 转换时间为秒
                const timeSeconds = this.parseTimeToSeconds(timeText);

                subtitles.push({
                    timeText,
                    time: timeSeconds,
                    english,
                    chinese
                });
            }
        }

        return subtitles;
    },

    // 将时间字符串转换为秒
    parseTimeToSeconds(timeStr) {
        const parts = timeStr.split(':');
        const minutes = parseInt(parts[0]) || 0;
        const seconds = parseInt(parts[1]) || 0;
        return minutes * 60 + seconds;
    },



    // 创建音频上下文
    createAudioContext() {
        this.audioContext = wx.createInnerAudioContext();
        this.audioContext.src = '/mock/solar.mp3';
        this.audioContext.autoplay = false;

        // 监听音频事件
        this.audioContext.onCanplay(() => {
            console.log('音频可以播放');
        });

        this.audioContext.onPlay(() => {
            this.setData({ isPlaying: true });
            this.startUpdateTimer();
        });

        this.audioContext.onPause(() => {
            this.setData({ isPlaying: false });
            this.stopUpdateTimer();
        });

        this.audioContext.onStop(() => {
            this.setData({ isPlaying: false });
            this.stopUpdateTimer();
        });

        this.audioContext.onEnded(() => {
            this.setData({ isPlaying: false });
            this.stopUpdateTimer();
        });

        this.audioContext.onError((error) => {
            console.error('音频播放错误:', error);
            wx.showToast({
                title: '音频加载失败',
                icon: 'none'
            });
        });
    },

    // 开始更新定时器
    startUpdateTimer() {
        this.updateTimer = setInterval(() => {
            if (this.audioContext) {
                const currentTime = this.audioContext.currentTime;
                this.setData({ currentTime });
                this.updateCurrentSubtitle(currentTime);
            }
        }, 100);
    },

    // 停止更新定时器
    stopUpdateTimer() {
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
            this.updateTimer = null;
        }
    },

    // 更新当前字幕
    updateCurrentSubtitle(currentTime) {
        const { subtitles, isLooping, currentIndex } = this.data;
        let newIndex = 0;

        for (let i = 0; i < subtitles.length; i++) {
            if (currentTime >= subtitles[i].time) {
                newIndex = i;
            } else {
                break;
            }
        }

        // 循环播放逻辑
        if (isLooping && currentIndex < subtitles.length) {
            const currentSubtitle = subtitles[currentIndex];
            const nextSubtitle = subtitles[currentIndex + 1];

            // 如果有下一个字幕，检查是否接近当前字幕结束
            if (nextSubtitle && currentTime >= (nextSubtitle.time - 0.1)) {
                // 跳回到当前字幕开始
                this.audioContext.seek(currentSubtitle.time);
                return;
            }
            // 如果是最后一个字幕，检查是否播放了足够长时间（假设每句至少3秒）
            else if (!nextSubtitle && currentTime >= (currentSubtitle.time + 3)) {
                this.audioContext.seek(currentSubtitle.time);
                return;
            }
        }

        if (newIndex !== this.data.currentIndex) {
            this.setScrollAlignment(newIndex);
            this.setData({
                currentIndex: newIndex,
                currentSubtitleId: `subtitle-${newIndex}`
            });
        }
    },

    // 播放/暂停
    onPlayPause() {
        if (this.data.isPlaying) {
            this.audioContext.pause();
        } else {
            this.audioContext.play();
        }
    },

    // 上一句
    onPrevious() {
        const { currentIndex, subtitles } = this.data;
        if (currentIndex > 0) {
            const newIndex = currentIndex - 1;
            const time = subtitles[newIndex].time;
            this.audioContext.seek(time);
            this.setScrollAlignment(newIndex);
            this.setData({
                currentIndex: newIndex,
                currentSubtitleId: `subtitle-${newIndex}`,
                currentTime: time
            });
        }
    },

    // 下一句
    onNext() {
        const { currentIndex, subtitles } = this.data;
        if (currentIndex < subtitles.length - 1) {
            const newIndex = currentIndex + 1;
            const time = subtitles[newIndex].time;
            this.audioContext.seek(time);
            this.setScrollAlignment(newIndex);
            this.setData({
                currentIndex: newIndex,
                currentSubtitleId: `subtitle-${newIndex}`,
                currentTime: time
            });
        }
    },

    // 点击字幕
    onSubtitleTap(e) {
        const index = e.currentTarget.dataset.index;
        const time = this.data.subtitles[index].time;
        this.audioContext.seek(time);
        this.setScrollAlignment(index);
        this.setData({
            currentIndex: index,
            currentSubtitleId: `subtitle-${index}`,
            currentTime: time
        });
    },

    // 进度条改变
    onProgressChange(e) {
        const time = e.detail.value;
        this.audioContext.seek(time);
        this.setData({ currentTime: time });
        this.updateCurrentSubtitle(time);
    },

    onProgressChanging(e) {
        const time = e.detail.value;
        this.setData({ currentTime: time });
        this.updateCurrentSubtitle(time);
    },

    // 收藏
    onFavorite() {
        const isFavorited = !this.data.isFavorited;
        this.setData({ isFavorited });

        // 保存收藏状态到本地存储
        wx.setStorageSync(`favorite_${this.data.articleId}`, isFavorited);

        wx.showToast({
            title: isFavorited ? '已收藏' : '已取消收藏',
            icon: 'success',
            duration: 1000
        });
    },

    // 加载收藏状态
    loadFavoriteStatus() {
        const isFavorited = wx.getStorageSync(`favorite_${this.data.articleId}`) || false;
        this.setData({ isFavorited });
    },

    // 单词按钮 - 显示单词卡片
    onDict() {
        const { articleId, title } = this.data;

        // 设置单词卡片数据
        this.setData({
            vocabularyTitle: '南非能源危机 单词',
            vocabularyWords: articleDetailData.vocabulary || [],
            showVocabulary: true
        });
    },


    // 关闭单词卡片
    onCloseVocabulary() {
        this.setData({ showVocabulary: false });
    },

    // 单词点击事件
    onWordTap(e) {
        const word = e.currentTarget.dataset.word;
        console.log('点击单词:', word);
        // 这里可以添加单词详情或发音功能
    },

    // 切换收藏状态
    onToggleFavorite(e) {
        const wordId = e.currentTarget.dataset.id;
        const vocabularyWords = this.data.vocabularyWords.map(word => {
            if (word.id === wordId) {
                return { ...word, isFavorited: !word.isFavorited };
            }
            return word;
        });
        
        this.setData({ vocabularyWords });
        
        const word = vocabularyWords.find(w => w.id === wordId);
        wx.showToast({
            title: word.isFavorited ? '已收藏' : '已取消收藏',
            icon: 'success',
            duration: 1000
        });
    },

    // 卡片手势处理相关变量
    cardStartY: 0,
    cardCurrentY: 0,
    cardMoving: false,

    // 卡片触摸开始
    onCardTouchStart(e) {
        this.cardStartY = e.touches[0].clientY;
        this.cardCurrentY = e.touches[0].clientY;
        this.cardMoving = false;
    },

    // 卡片触摸移动
    onCardTouchMove(e) {
        if (!this.data.showVocabulary) return;
        
        this.cardCurrentY = e.touches[0].clientY;
        const deltaY = this.cardCurrentY - this.cardStartY;
        
        // 只允许向下滑动
        if (deltaY > 0) {
            this.cardMoving = true;
            // 这里可以添加实时拖拽效果，暂时简化处理
        }
    },

    // 卡片触摸结束
    onCardTouchEnd(e) {
        if (!this.data.showVocabulary || !this.cardMoving) return;
        
        const deltaY = this.cardCurrentY - this.cardStartY;
        const threshold = 100; // 关闭阈值
        
        if (deltaY > threshold) {
            // 向下滑动超过阈值，关闭卡片
            this.onCloseVocabulary();
        }
        
        // 重置状态
        this.cardMoving = false;
        this.cardStartY = 0;
        this.cardCurrentY = 0;
    },

    // 循环播放当前字幕
    onRepeat() {
        const { isLooping } = this.data;
        this.setData({ isLooping: !isLooping });

        wx.showToast({
            title: isLooping ? '取消循环' : '循环播放当前句',
            icon: 'none',
            duration: 1000
        });
    },

    // 字幕设置 - 切换单英语和双语模式
    onSubtitleSettings() {
        const { showChinese } = this.data;
        this.setData({ showChinese: !showChinese });

        wx.showToast({
            title: showChinese ? '英语模式' : '双语模式',
            icon: 'none',
            duration: 1000
        });
    },

    // 播放速度控制 - 循环切换速度
    onSettings() {
        const { playSpeed, speedOptions } = this.data;
        const currentIndex = speedOptions.indexOf(playSpeed);
        const nextIndex = (currentIndex + 1) % speedOptions.length;
        const newSpeed = speedOptions[nextIndex];

        this.setData({ playSpeed: newSpeed });
        this.audioContext.playbackRate = newSpeed;

        wx.showToast({
            title: `播放速度: ${newSpeed}x`,
            icon: 'none',
            duration: 1000
        });
    },

    // 关闭设置
    onCloseSettings() {
        this.setData({ showSettings: false });
    },

    // 阻止冒泡
    stopPropagation() {
        // 空函数，阻止冒泡
    },

    // 播放速度改变
    onSpeedChange(e) {
        const speed = parseFloat(e.currentTarget.dataset.speed);
        this.setData({ playSpeed: speed });
        this.audioContext.playbackRate = speed;

        wx.showToast({
            title: `播放速度: ${speed}x`,
            icon: 'none',
            duration: 1000
        });
    },

    // 字幕模式改变
    onSubtitleModeChange(e) {
        const mode = e.currentTarget.dataset.mode;
        const showChinese = mode === 'both';
        this.setData({ showChinese });

        wx.showToast({
            title: showChinese ? '双语模式' : '英语模式',
            icon: 'none',
            duration: 1000
        });
    },

    // 获取容器高度
    getContainerHeight() {
        const query = wx.createSelectorQuery().in(this);
        query.select('.subtitle-container').boundingClientRect();
        query.exec((res) => {
            if (res[0]) {
                this.setData({ containerHeight: res[0].height });
            }
        });
    },

    // 设置滚动偏移量（歌词式逻辑）
    setScrollAlignment(index) {
        const { subtitles, containerHeight } = this.data;

        if (containerHeight === 0) return;

        // 计算居中偏移量（负值表示向上偏移，让目标元素显示在中心）
        const centerOffset = -(containerHeight / 3 - 60); // 60是大概的字幕项高度的一半        
        this.setData({ scrollOffset: centerOffset });
    }
}); 