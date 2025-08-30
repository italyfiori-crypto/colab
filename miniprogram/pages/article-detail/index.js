Page({
    data: {
        // 章节信息
        chapterId: null,
        bookId: null,
        chapterData: {},
        title: '',
        book_title: '',

        // 字幕数据
        subtitles: [],
        currentIndex: 0,
        currentSubtitleId: '',
        subtitleMode: 'both', // 'en': 仅英语, 'zh': 仅中文, 'both': 双语
        scrollOffset: 0,
        containerHeight: 0,

        // 音频控制
        isPlaying: false,
        currentTime: 0,
        duration: 0, // 从数据库获取
        playSpeed: 1,
        speedOptions: [0.7, 0.85, 1.0, 1.25],
        isLooping: false, // 循环播放当前字幕
        manualControl: false, // 手动控制标志

        // UI状态
        isFavorited: false,
        showVocabulary: false,
        loading: true,

        // 单词卡片数据
        vocabularyTitle: '',
        vocabularyWords: [],

        // 进度相关
        isCompleted: false,
        isProgressUpdated: false
    },

    onLoad(options) {
        const chapterId = options.chapterId;
        const bookId = options.bookId;
        const chapterTitle = options.chapterTitle ? decodeURIComponent(options.chapterTitle) : '';

        this.setData({
            chapterId,
            bookId,
            title: chapterTitle
        });

        // 设置导航栏标题
        wx.setNavigationBarTitle({
            title: chapterTitle || '英语学习'
        });

        // 加载章节详情数据
        this.loadChapterData();

        // 加载收藏状态
        this.loadFavoriteStatus();

        // 获取容器高度
        this.getContainerHeight();
    },

    onUnload() {
        // 保存当前播放进度
        this.saveCurrentProgress();
        
        // 清理音频
        if (this.audioContext) {
            this.audioContext.destroy();
            this.audioContext = null;
        }
        // 清理定时器
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
            this.updateTimer = null;
        }
        // 清理手动控制定时器
        if (this.manualControlTimer) {
            clearTimeout(this.manualControlTimer);
            this.manualControlTimer = null;
        }
    },

    // 加载章节数据
    async loadChapterData() {
        try {
            this.setData({ loading: true });

            wx.showLoading({
                title: '加载中...'
            });

            // 调用云函数获取章节详情
            const result = await wx.cloud.callFunction({
                name: 'articleDetailData',
                data: {
                    type: 'getChapterDetail',
                    chapterId: this.data.chapterId
                }
            });

            wx.hideLoading();

            if (result.result.code === 0) {
                const chapterData = result.result.data;

                this.setData({
                    chapterData,
                    title: chapterData.title,
                    book_title: chapterData.book_title,
                    duration: chapterData.duration,
                    isCompleted: chapterData.is_completed,
                    loading: false
                });

                // 设置导航栏标题
                wx.setNavigationBarTitle({
                    title: chapterData.title || '英语学习'
                });

                // 立即加载字幕数据
                if (chapterData.subtitle_url) {
                    this.loadSubtitlesFromCloud(chapterData.subtitle_url);
                } else {
                    // 如果没有字幕URL，提示用户
                    wx.showToast({
                        title: '该章节暂无字幕数据',
                        icon: 'none',
                        duration: 2000
                    });
                }

                // 音频URL存储，播放时再加载
                this.audioUrl = chapterData.audio_url;
                this.audioContext = null; // 初始时不创建音频对象

            } else {
                wx.showToast({
                    title: result.result.message || '获取章节数据失败',
                    icon: 'none',
                    duration: 2000
                });
                this.setData({ loading: false });
            }

        } catch (error) {
            wx.hideLoading();
            console.error('加载章节数据失败:', error);
            wx.showToast({
                title: '网络异常，请重试',
                icon: 'none',
                duration: 2000
            });
            this.setData({ loading: false });
        }
    },

    // 从云存储加载字幕数据
    loadSubtitlesFromCloud(subtitleUrl) {
        if (!subtitleUrl) {
            console.error('字幕URL为空');
            wx.showToast({
                title: '字幕数据不存在',
                icon: 'none',
                duration: 2000
            });
            return;
        }

        console.log('开始从云存储加载字幕数据:', subtitleUrl);

        wx.showLoading({
            title: '加载字幕中...'
        });

        // 从云存储下载SRT文件
        wx.cloud.downloadFile({
            fileID: subtitleUrl,
            success: res => {
                wx.hideLoading();
                console.log('字幕文件下载成功:', res.tempFilePath);

                // 解析SRT文件内容
                this.parseSRTFile(res.tempFilePath);
            },
            fail: err => {
                wx.hideLoading();
                console.error('字幕文件下载失败:', err);
                wx.showToast({
                    title: '字幕加载失败',
                    icon: 'none',
                    duration: 2000
                });
            }
        });
    },

    // 解析SRT文件
    parseSRTFile(filePath) {
        console.log('开始解析SRT文件:', filePath);

        const fs = wx.getFileSystemManager();

        try {
            // 读取文件内容
            const fileContent = fs.readFileSync(filePath, 'utf8');
            console.log('SRT文件内容读取成功');

            // 解析SRT格式内容
            const subtitles = this.parseSRTContent(fileContent);

            if (subtitles && subtitles.length > 0) {
                this.setData({ subtitles });
                wx.showToast({
                    title: `字幕加载成功 (${subtitles.length}条)`,
                    icon: 'success',
                    duration: 1500
                });
                console.log('字幕解析完成:', subtitles.length, '条');
            } else {
                this.setData({ subtitles: [] });
                wx.showToast({
                    title: '字幕文件格式错误',
                    icon: 'none',
                    duration: 2000
                });
            }
        } catch (error) {
            console.error('SRT文件解析失败:', error);
            this.setData({ subtitles: [] });
            wx.showToast({
                title: '字幕文件解析失败',
                icon: 'none',
                duration: 2000
            });
        }
    },

    // 解析SRT内容
    parseSRTContent(content) {
        if (!content || typeof content !== 'string') {
            return [];
        }

        console.log('解析SRT内容，长度:', content.length);

        const subtitles = [];
        const blocks = content.trim().split(/\n\s*\n/); // 按空行分割字幕块

        for (let i = 0; i < blocks.length; i++) {
            const block = blocks[i].trim();
            if (!block) continue;

            const lines = block.split('\n');
            if (lines.length < 3) continue;

            try {
                const index = parseInt(lines[0]); // 字幕序号
                const timeRange = lines[1]; // 时间范围
                const english = lines[2] || ''; // 英文内容
                const chinese = lines[3] || ''; // 中文内容（可选）

                // 解析开始时间
                const startTime = this.parseSRTTimeToSeconds(timeRange.split(' --> ')[0]);

                if (startTime !== null) {
                    subtitles.push({
                        index,
                        timeText: this.formatSecondsToTime(startTime),
                        time: startTime,
                        english: english.trim(),
                        chinese: chinese.trim()
                    });
                }
            } catch (error) {
                console.warn('解析字幕块失败:', block, error);
            }
        }

        return subtitles;
    },

    // 将SRT时间格式转换为秒 (HH:MM:SS,mmm)
    parseSRTTimeToSeconds(timeStr) {
        if (!timeStr) return null;

        try {
            const parts = timeStr.split(':');
            const hours = parseInt(parts[0]) || 0;
            const minutes = parseInt(parts[1]) || 0;
            const secondsParts = parts[2].split(',');
            const seconds = parseInt(secondsParts[0]) || 0;
            const milliseconds = parseInt(secondsParts[1]) || 0;

            return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000;
        } catch (error) {
            console.warn('时间格式解析失败:', timeStr, error);
            return null;
        }
    },

    // 将秒转换为显示时间格式
    formatSecondsToTime(seconds) {
        if (seconds == null || seconds < 0) return '0:00';

        const minutes = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    },

    // 创建音频上下文
    createAudioContext(audioUrl) {
        this.audioContext = wx.createInnerAudioContext();
        this.audioContext.src = audioUrl; // 使用数据库中的音频URL
        this.audioContext.autoplay = false;

        // 立即应用当前播放速度
        this.audioContext.playbackRate = this.data.playSpeed;

        // 监听音频事件
        this.audioContext.onCanplay(() => {
            console.log('音频可以播放');
            // 确保播放速度设置生效
            this.audioContext.playbackRate = this.data.playSpeed;
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

            // 播放完成后标记章节完成并更新学习进度
            this.updateLearningProgress(true); // true表示章节完成
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
        }, 50); // 提高到50ms间隔，增强真机同步精度
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
        const { subtitles, isLooping, currentIndex, manualControl } = this.data;
        let newIndex = 0;

        for (let i = 0; i < subtitles.length; i++) {
            if (currentTime >= subtitles[i].time) {
                newIndex = i;
            } else {
                break;
            }
        }

        // 循环播放逻辑 - 只在非手动控制时执行
        if (isLooping && !manualControl && currentIndex < subtitles.length) {
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
            this.setScrollAlignment();
            this.setData({
                currentIndex: newIndex,
                currentSubtitleId: `subtitle-${newIndex}`
            });
        }
    },

    // 播放/暂停
    onPlayPause() {
        if (!this.audioContext) {
            // 首次播放时创建音频对象
            this.createAudioContextOnDemand();
            return;
        }

        if (this.data.isPlaying) {
            this.audioContext.pause();
        } else {
            this.audioContext.play();
        }
    },

    // 按需创建音频上下文
    createAudioContextOnDemand() {
        console.log('按需创建音频上下文:', this.audioUrl);

        if (!this.audioUrl) {
            wx.showToast({
                title: '该章节暂无音频数据',
                icon: 'none',
                duration: 2000
            });
            return;
        }

        wx.showLoading({
            title: '加载音频中...'
        });

        this.createAudioContext(this.audioUrl);

        // 音频准备好后自动播放
        this.audioContext.onCanplay(() => {
            wx.hideLoading();
            this.audioContext.play();
        });

        this.audioContext.onError(() => {
            wx.hideLoading();
            wx.showToast({
                title: '音频加载失败',
                icon: 'none',
                duration: 2000
            });
        });
    },

    // 上一句
    onPrevious() {
        const { currentIndex, subtitles } = this.data;
        if (currentIndex > 0 && this.audioContext) {
            const newIndex = currentIndex - 1;
            const time = subtitles[newIndex].time;

            // 设置手动控制标志
            this.setManualControl();

            this.audioContext.seek(time);
            this.setScrollAlignment();
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
        if (currentIndex < subtitles.length - 1 && this.audioContext) {
            const newIndex = currentIndex + 1;
            const time = subtitles[newIndex].time;

            // 设置手动控制标志
            this.setManualControl();

            this.audioContext.seek(time);
            this.setScrollAlignment();
            this.setData({
                currentIndex: newIndex,
                currentSubtitleId: `subtitle-${newIndex}`,
                currentTime: time
            });
        }
    },

    // 点击字幕
    onSubtitleTap(e) {
        if (!this.audioContext) {
            // 如果音频还未加载，创建音频上下文
            this.createAudioContextOnDemand();
            return;
        }
        
        const index = e.currentTarget.dataset.index;
        const time = this.data.subtitles[index].time;

        // 设置手动控制标志
        this.setManualControl();

        this.audioContext.seek(time);
        this.setScrollAlignment();
        this.setData({
            currentIndex: index,
            currentSubtitleId: `subtitle-${index}`,
            currentTime: time
        });
    },

    // 进度条改变
    onProgressChange(e) {
        if (!this.audioContext) {
            return;
        }
        
        const time = e.detail.value;

        // 设置手动控制标志
        this.setManualControl();

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
        wx.setStorageSync(`favorite_${this.data.chapterId}`, isFavorited);

        wx.showToast({
            title: isFavorited ? '已收藏' : '已取消收藏',
            icon: 'success',
            duration: 1000
        });
    },

    // 加载收藏状态
    loadFavoriteStatus() {
        const isFavorited = wx.getStorageSync(`favorite_${this.data.chapterId}`) || false;
        this.setData({ isFavorited });
    },

    // 单词按钮 - 显示单词卡片
    async onDict() {
        try {
            wx.showLoading({
                title: '加载单词中...'
            });

            // 调用云函数获取章节单词
            const result = await wx.cloud.callFunction({
                name: 'articleDetailData',
                data: {
                    type: 'getChapterVocabularies',
                    chapterId: this.data.chapterId
                }
            });

            wx.hideLoading();

            if (result.result.code === 0) {
                const { chapter_title, vocabularies } = result.result.data;

                this.setData({
                    vocabularyTitle: `${chapter_title} 单词`,
                    vocabularyWords: vocabularies,
                    showVocabulary: true
                });
            } else {
                wx.showToast({
                    title: result.result.message || '获取单词失败',
                    icon: 'none',
                    duration: 2000
                });
            }

        } catch (error) {
            wx.hideLoading();
            console.error('加载单词失败:', error);
            wx.showToast({
                title: '网络异常，请重试',
                icon: 'none',
                duration: 2000
            });
        }
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
    onCardTouchEnd() {
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

    // 字幕设置 - 循环切换三种模式
    onSubtitleSettings() {
        const { subtitleMode } = this.data;
        const modes = ['en', 'zh', 'both'];
        const currentIndex = modes.indexOf(subtitleMode);
        const nextIndex = (currentIndex + 1) % modes.length;
        const newMode = modes[nextIndex];

        this.setData({ subtitleMode: newMode });

        const modeNames = {
            'en': '英语模式',
            'zh': '中文模式',
            'both': '双语模式'
        };

        wx.showToast({
            title: modeNames[newMode],
            icon: 'none',
            duration: 1000
        });
    },

    // 播放速度控制 - 循环切换速度
    onSpeedChange() {
        const { playSpeed, speedOptions, isPlaying } = this.data;
        const currentIndex = speedOptions.indexOf(playSpeed);
        const nextIndex = (currentIndex + 1) % speedOptions.length;
        const newSpeed = speedOptions[nextIndex];

        this.setData({ playSpeed: newSpeed });

        // 如果音频对象已存在，立即应用速度并强制重新播放
        if (this.audioContext) {
            this.audioContext.playbackRate = newSpeed;
            
            // 如果正在播放，先暂停再播放以让速度立即生效
            if (isPlaying) {
                this.audioContext.pause();
                setTimeout(() => {
                    this.audioContext.play();
                }, 50); // 短暂延迟确保暂停生效
            }
        }

        wx.showToast({
            title: `播放速度: ${newSpeed}x`,
            icon: 'none',
            duration: 1000
        });
    },

    // 设置手动控制标志
    setManualControl() {
        this.setData({ manualControl: true });

        // 2秒后清除手动控制标志，允许循环播放恢复
        if (this.manualControlTimer) {
            clearTimeout(this.manualControlTimer);
        }
        this.manualControlTimer = setTimeout(() => {
            this.setData({ manualControl: false });
        }, 2000);
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
    setScrollAlignment() {
        const { containerHeight } = this.data;

        if (containerHeight === 0) return;

        // 计算居中偏移量（负值表示向上偏移，让目标元素显示在中心）
        const centerOffset = -(containerHeight / 3 - 60); // 60是大概的字幕项高度的一半        
        this.setData({ scrollOffset: centerOffset });
    },

    // 保存当前播放进度
    async saveCurrentProgress() {
        if (!this.data.chapterId || !this.data.bookId || !this.audioContext) {
            return;
        }

        try {
            const currentTime = this.audioContext.currentTime || this.data.currentTime;
            
            await wx.cloud.callFunction({
                name: 'articleDetailData',
                data: {
                    type: 'saveChapterProgress',
                    bookId: this.data.bookId,
                    chapterId: this.data.chapterId,
                    currentTime: currentTime,
                    completed: false
                }
            });

            console.log(`章节进度已保存: ${currentTime}秒`);
        } catch (error) {
            console.error('保存章节进度失败:', error);
        }
    },

    // 更新学习进度
    async updateLearningProgress(isCompleted = false) {
        if (!this.data.chapterId || !this.data.bookId) {
            return;
        }

        try {
            console.log('更新学习进度:', this.data.chapterId, isCompleted ? '(完成)' : '(进度)');

            const currentTime = this.audioContext ? this.audioContext.currentTime : this.data.currentTime;

            // 调用云函数更新学习进度
            const result = await wx.cloud.callFunction({
                name: 'articleDetailData',
                data: {
                    type: 'saveChapterProgress',
                    bookId: this.data.bookId,
                    chapterId: this.data.chapterId,
                    currentTime: currentTime || 0,
                    completed: isCompleted
                }
            });

            if (result.result.code === 0) {
                if (isCompleted) {
                    this.setData({
                        isProgressUpdated: true,
                        isCompleted: true
                    });

                    wx.showToast({
                        title: '章节学习完成！',
                        icon: 'success',
                        duration: 1500
                    });
                }

                console.log('学习进度更新成功');
            } else {
                console.error('学习进度更新失败:', result.result.message);
            }

        } catch (error) {
            console.error('更新学习进度异常:', error);
        }
    }
});