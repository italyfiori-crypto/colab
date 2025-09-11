// 文章详情页逻辑
const settingsUtils = require('../../utils/settingsUtils.js');

Page({
    data: {
        // 章节信息
        chapterId: null,
        bookId: null,
        chapterData: {},
        title: '',

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
        speedOptions: [0.8, 0.9, 1.0, 1.1, 1.2, 1.3], // 扩展速度选项
        isLooping: false, // 循环播放当前字幕
        manualControl: false, // 手动控制标志

        // UI状态
        isFavorited: false,
        showVocabulary: false,
        loading: true,
        wasPlayingBeforeVocabulary: false, // 显示单词卡片前的播放状态

        // 单词卡片数据
        vocabularyWords: [],
        currentPage: 1,
        hasMoreWords: true,
        loadingMore: false,

        // 单词详情弹窗
        showWordDetail: false,
        currentWord: {},

        // 缓存数据
        wordDetailCache: {}, // 单词信息缓存
        audioCache: {}, // 音频实例缓存

        // 用户设置
        userSettings: {}
    },

    async onLoad(options) {
        const chapterId = options.chapterId;
        const bookId = options.bookId;
        const chapterTitle = options.chapterTitle ? decodeURIComponent(options.chapterTitle) : '';

        // 加载用户设置并初始化页面
        await this.loadUserSettings();

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

    /**
     * 加载用户设置并应用
     */
    async loadUserSettings() {
        const userInfo = await settingsUtils.getCompleteUserInfo();
        const readingSettings = userInfo.reading_settings || {};

        // 应用字幕语言设置
        const subtitleMode = settingsUtils.mapSubtitleLangToMode(readingSettings.subtitle_lang || '中英双语');

        // 应用播放速度设置
        const playSpeed = readingSettings.playback_speed || 1.0;

        this.setData({
            userSettings: userInfo,
            subtitleMode: subtitleMode,
            playSpeed: playSpeed
        });

        console.log('✅ [DEBUG] 用户设置已应用:', {
            字幕模式: subtitleMode,
            播放速度: playSpeed,
            原始设置: readingSettings.subtitleLang
        });
    },

    onUnload() {
        // 保存当前播放进度
        this.saveCurrentProgress();

        // 清理音频
        if (this.audioContext) {
            this.audioContext.destroy();
            this.audioContext = null;
        }

        // 清理缓存的单词音频实例
        const audioCache = this.data.audioCache;
        Object.values(audioCache).forEach(audio => {
            if (audio && audio.destroy) {
                audio.destroy();
            }
        });

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
                    duration: chapterData.duration,
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
                        chinese: chinese.trim(),
                        englishWords: this.parseEnglishWords(english.trim()) // 分解英文单词
                    });
                }
            } catch (error) {
                console.warn('解析字幕块失败:', block, error);
            }
        }

        return subtitles;
    },

    // 分解英文句子为可点击的单词和标点符号
    parseEnglishWords(text) {
        if (!text) return [];

        const words = [];
        // 使用正则表达式分割，保留单词和标点符号
        const tokens = text.match(/\w+|[^\w\s]/g) || [];

        for (let i = 0; i < tokens.length; i++) {
            const token = tokens[i];
            const isWord = /\w+/.test(token); // 判断是否为单词

            words.push({
                text: token,
                isWord: isWord
            });

            // 在单词/标点后添加空格（除了最后一个元素）
            if (i < tokens.length - 1) {
                const nextToken = tokens[i + 1];
                // 如果下一个不是标点符号，则添加空格
                if (/\w/.test(nextToken)) {
                    words.push({
                        text: ' ',
                        isWord: false
                    });
                }
            }
        }

        return words;
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

    // 时间点击事件（跳转播放进度）
    onTimeClick(e) {
        if (!this.audioContext) {
            // 如果音频还未加载，创建音频上下文
            this.createAudioContextOnDemand();
            return;
        }

        const time = e.currentTarget.dataset.time;
        const index = e.currentTarget.dataset.index;

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

    // 单词点击事件
    async onWordClick(e) {
        const word = e.currentTarget.dataset.word;
        if (!word || word.trim().length < 2) {
            return; // 忽略过短的单词或空字符
        }

        console.log('点击单词:', word);
        const cacheKey = word.toLowerCase();

        // 检查缓存
        if (this.data.wordDetailCache[cacheKey]) {
            console.log('从缓存加载单词信息:', word, this.data.wordDetailCache[cacheKey]);
            const cachedWordData = this.data.wordDetailCache[cacheKey];
            this.setData({
                currentWord: cachedWordData,
                showWordDetail: true
            });
            return;
        }

        try {
            wx.showLoading({
                title: '加载单词信息...'
            });

            // 调用云函数获取单词详情
            const result = await wx.cloud.callFunction({
                name: 'articleDetailData',
                data: {
                    type: 'getWordDetail',
                    word: word.toLowerCase(),
                    bookId: this.data.bookId,
                    chapterId: this.data.chapterId
                }
            });

            wx.hideLoading();

            if (result.result.code === 0) {
                const wordData = result.result.data;
                // 添加标签中文翻译
                wordData.translatedTags = this.translateTags(wordData.tags || []);

                // 缓存单词信息
                this.setData({
                    [`wordDetailCache.${cacheKey}`]: wordData,
                    currentWord: wordData,
                    showWordDetail: true
                });
            } else {
                wx.showToast({
                    title: result.result.message || '获取单词信息失败',
                    icon: 'none',
                    duration: 2000
                });
            }

        } catch (error) {
            wx.hideLoading();
            console.error('获取单词详情失败:', error);
            wx.showToast({
                title: '网络异常，请重试',
                icon: 'none',
                duration: 2000
            });
        }
    },

    // 关闭单词详情弹窗
    onCloseWordDetail() {
        this.setData({
            showWordDetail: false,
            currentWord: {}
        });
    },

    // 翻译标签为中文
    translateTags(tags) {
        const tagMap = {
            'zk': '中考',
            'gk': '高考',
            'ky': '考研',
            'cet4': '四级',
            'cet6': '六级',
            'toefl': '托福',
            'ielts': '雅思',
            'gre': 'GRE'
        };

        if (typeof tags === 'string') {
            // 如果tags是字符串，先按空格分割
            tags = tags.split(' ').filter(tag => tag.trim());
        }

        return (tags || []).map(tag => tagMap[tag.trim()] || tag.trim()).filter(tag => tag);
    },

    // 播放单词音频
    onPlayAudio(e) {
        const type = e.currentTarget.dataset.type; // 'uk' 或 'us'
        const audioUrl = this.data.currentWord[`audio_url_${type}`];

        if (!audioUrl) {
            wx.showToast({
                title: `${type === 'uk' ? '英' : '美'}音暂不可用`,
                icon: 'none',
                duration: 1500
            });
            return;
        }

        // 显示播放提示
        wx.showToast({
            title: `播放${type === 'uk' ? '英' : '美'}音`,
            icon: 'none',
            duration: 800
        });

        const cacheKey = `${this.data.currentWord.word}_${type}`;

        // 检查音频缓存
        if (this.data.audioCache[cacheKey]) {
            const cachedAudio = this.data.audioCache[cacheKey];
            // 重置到开始位置并播放
            cachedAudio.seek(0);
            cachedAudio.play();
            return;
        }

        // 创建新的音频实例
        const wordAudio = wx.createInnerAudioContext();
        wordAudio.src = audioUrl;
        wordAudio.autoplay = true;

        // 缓存音频实例
        this.setData({
            [`audioCache.${cacheKey}`]: wordAudio
        });

        wordAudio.onError((error) => {
            console.error('单词音频播放失败:', error);
            wx.showToast({
                title: '音频播放失败',
                icon: 'none',
                duration: 1500
            });
            // 从缓存中移除失败的音频实例
            const audioCache = { ...this.data.audioCache };
            delete audioCache[cacheKey];
            this.setData({ audioCache });
        });

        wordAudio.onEnded(() => {
            // 音频播放完成后不销毁，保留在缓存中以便重复播放
            console.log('音频播放完成，保留在缓存中');
        });
    },

    // 切换单词收藏状态
    async onToggleWordCollection() {
        const { currentWord } = this.data;
        if (!currentWord.word) return;

        try {
            wx.showLoading({
                title: currentWord.is_favorited ? '移除中...' : '添加中...'
            });

            const result = await wx.cloud.callFunction({
                name: 'articleDetailData',
                data: {
                    type: currentWord.is_favorited ? 'removeWordFromCollection' : 'addWordToCollection',
                    word: currentWord.word,
                    wordId: currentWord._id || currentWord.id,
                    bookId: this.data.bookId,
                    chapterId: this.data.chapterId
                }
            });

            wx.hideLoading();

            if (result.result.code === 0) {
                const newCollectedStatus = !currentWord.is_favorited;
                this.setData({
                    'currentWord.is_favorited': newCollectedStatus
                });

                wx.showToast({
                    title: newCollectedStatus ? '已加入单词本' : '已从单词本移除',
                    icon: 'success',
                    duration: 1500
                });
            } else {
                wx.showToast({
                    title: result.result.message || '操作失败',
                    icon: 'none',
                    duration: 2000
                });
            }

        } catch (error) {
            wx.hideLoading();
            console.error('单词收藏操作失败:', error);
            wx.showToast({
                title: '网络异常，请重试',
                icon: 'none',
                duration: 2000
            });
        }
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
        console.log('字典按钮被点击');

        // 重置分页状态
        this.setData({
            currentPage: 1,
            hasMoreWords: true,
            vocabularyWords: []
        });

        await this.loadVocabularyWords(1, true);
    },

    // 加载单词数据的通用函数
    async loadVocabularyWords(page = 1, isFirstLoad = false) {
        try {
            // 显示加载状态
            if (isFirstLoad) {
                wx.showLoading({
                    title: '加载单词中...'
                });
            } else {
                this.setData({ loadingMore: true });
            }

            // 调用云函数获取章节单词
            const result = await wx.cloud.callFunction({
                name: 'articleDetailData',
                data: {
                    type: 'getChapterVocabularies',
                    chapterId: this.data.chapterId,
                    page: page,
                    pageSize: 20
                }
            });

            if (isFirstLoad) {
                wx.hideLoading();
            } else {
                this.setData({ loadingMore: false });
            }

            if (result.result.code === 0) {
                const { vocabularies, hasMore } = result.result.data;
                console.log("vocabularies:", result.result.data)

                // 限制每个单词最多显示3行释义，并添加基于用户偏好的音标和音频
                const processedVocabularies = vocabularies.map(word => {
                    const baseWord = {
                        ...word,
                        translation: word.translation ? word.translation.slice(0, 3) : []
                    };
                    
                    // 根据用户设置选择音标和音频
                    const voiceType = this.data.userSettings.learning_settings?.voice_type || '美式发音';
                    if (voiceType === '美式发音') {
                        baseWord.displayPhonetic = word.phonetic_us || word.phonetic_uk || '';
                        baseWord.audioUrl = word.audio_url_us || word.audio_url_uk || '';
                    } else {
                        baseWord.displayPhonetic = word.phonetic_uk || word.phonetic_us || '';
                        baseWord.audioUrl = word.audio_url_uk || word.audio_url_us || '';
                    }
                    
                    return baseWord;
                });

                if (isFirstLoad) {
                    // 首次加载，暂停音频播放并显示弹窗
                    const wasPlaying = this.data.isPlaying;
                    if (wasPlaying && this.audioContext) {
                        this.audioContext.pause();
                    }

                    this.setData({
                        vocabularyWords: processedVocabularies,
                        currentPage: page,
                        hasMoreWords: hasMore,
                        showVocabulary: true,
                        wasPlayingBeforeVocabulary: wasPlaying
                    });
                } else {
                    // 分页加载，追加数据
                    const existingWords = this.data.vocabularyWords;
                    const mergedWords = [...existingWords, ...processedVocabularies];

                    this.setData({
                        vocabularyWords: mergedWords,
                        currentPage: page,
                        hasMoreWords: hasMore
                    });
                }
            } else {
                if (isFirstLoad) {
                    wx.showToast({
                        title: result.result.message || '获取单词失败',
                        icon: 'none',
                        duration: 2000
                    });
                } else {
                    console.error('加载更多单词失败:', result.result.message);
                }
            }

        } catch (error) {
            if (isFirstLoad) {
                wx.hideLoading();
            } else {
                this.setData({ loadingMore: false });
            }
            console.error('加载单词失败:', error);
            if (isFirstLoad) {
                wx.showToast({
                    title: '网络异常，请重试',
                    icon: 'none',
                    duration: 2000
                });
            }
        }
    },

    // 滚动到底部加载更多
    async onScrollToLower() {
        const { hasMoreWords, loadingMore } = this.data;

        // 如果没有更多数据或正在加载中，则返回
        if (!hasMoreWords || loadingMore) {
            return;
        }

        console.log('滚动到底部，加载更多单词');
        const nextPage = this.data.currentPage + 1;
        await this.loadVocabularyWords(nextPage, false);
    },



    // 关闭单词卡片
    onCloseVocabulary() {
        this.setData({ showVocabulary: false });

        // 恢复音频播放
        if (this.data.wasPlayingBeforeVocabulary && this.audioContext) {
            this.audioContext.play();
        }

        this.setData({ wasPlayingBeforeVocabulary: false });
    },

    // 单词点击事件
    onWordTap(e) {
        const word = e.currentTarget.dataset.word;
        console.log('点击单词播放音频:', word);

        if (!word || !word.word) {
            console.error('单词数据无效:', word);
            return;
        }

        // 使用预处理好的音频URL，或者作为备用方案根据用户设置确定
        let audioUrl = word.audioUrl;
        let audioType = null;
        
        if (!audioUrl) {
            // 备用逻辑：如果没有预处理的audioUrl，重新根据用户设置选择
            const voiceType = this.data.userSettings.learning_settings?.voice_type || '美式发音';
            if (voiceType === '美式发音') {
                if (word.audio_url_us) {
                    audioUrl = word.audio_url_us;
                    audioType = 'us';
                } else if (word.audio_url_uk) {
                    audioUrl = word.audio_url_uk;
                    audioType = 'uk';
                }
            } else {
                if (word.audio_url_uk) {
                    audioUrl = word.audio_url_uk;
                    audioType = 'uk';
                } else if (word.audio_url_us) {
                    audioUrl = word.audio_url_us;
                    audioType = 'us';
                }
            }
        } else {
            // 从预处理的audioUrl推断类型
            if (word.audio_url_us && audioUrl === word.audio_url_us) {
                audioType = 'us';
            } else if (word.audio_url_uk && audioUrl === word.audio_url_uk) {
                audioType = 'uk';
            } else {
                audioType = 'us'; // 默认显示美式
            }
        }

        if (!audioUrl) {
            wx.showToast({
                title: '音频暂不可用',
                icon: 'none',
                duration: 1500
            });
            return;
        }

        // 显示播放提示
        wx.showToast({
            title: `播放${audioType === 'uk' ? '英' : '美'}音`,
            icon: 'none',
            duration: 800
        });

        const cacheKey = `${word.word}_${audioType}`;

        // 检查音频缓存
        if (this.data.audioCache[cacheKey]) {
            const cachedAudio = this.data.audioCache[cacheKey];
            // 应用当前播放速度
            cachedAudio.playbackRate = this.data.playSpeed;
            // 重置到开始位置并播放
            cachedAudio.seek(0);
            cachedAudio.play();
            return;
        }

        // 创建新的音频实例
        const wordAudio = wx.createInnerAudioContext();
        wordAudio.src = audioUrl;
        wordAudio.autoplay = true;
        // 应用用户设置的播放速度
        wordAudio.playbackRate = this.data.playSpeed;

        // 缓存音频实例
        this.setData({
            [`audioCache.${cacheKey}`]: wordAudio
        });

        wordAudio.onError((error) => {
            console.error('单词音频播放失败:', error);
            wx.showToast({
                title: '音频播放失败',
                icon: 'none',
                duration: 1500
            });
            // 从缓存中移除失败的音频实例
            const audioCache = { ...this.data.audioCache };
            delete audioCache[cacheKey];
            this.setData({ audioCache });
        });
    },

    // 切换收藏状态
    async onToggleFavorite(e) {
        const wordId = e.currentTarget.dataset.id;

        if (!wordId) {
            console.error('单词ID不存在:', wordId);
            wx.showToast({
                title: '操作失败，单词ID无效',
                icon: 'none',
                duration: 2000
            });
            return;
        }

        // 找到对应的单词
        const targetWord = this.data.vocabularyWords.find(w => w._id === wordId);
        if (!targetWord) {
            console.error('未找到对应单词:', wordId);
            wx.showToast({
                title: '操作失败，未找到单词',
                icon: 'none',
                duration: 2000
            });
            return;
        }

        try {
            // 显示加载状态
            wx.showLoading({
                title: targetWord.is_favorited ? '移除中...' : '添加中...'
            });

            // 调用云函数更新收藏状态
            const result = await wx.cloud.callFunction({
                name: 'articleDetailData',
                data: {
                    type: targetWord.is_favorited ? 'removeWordFromCollection' : 'addWordToCollection',
                    word: targetWord.word,
                    wordId: targetWord._id,
                    bookId: this.data.bookId,
                    chapterId: this.data.chapterId
                }
            });
            console.log("toggle word:", targetWord, this.data, this.data.vocabularyWords)

            wx.hideLoading();

            if (result.result.code === 0) {
                // 更新前端状态
                const vocabularyWords = this.data.vocabularyWords.map(word => {
                    if (word._id === wordId) {
                        return { ...word, is_favorited: !word.is_favorited };
                    }
                    return word;
                });

                this.setData({ vocabularyWords });

                const updatedWord = vocabularyWords.find(w => w._id === wordId);
                wx.showToast({
                    title: updatedWord.is_favorited ? '已加入单词本' : '已从单词本移除',
                    icon: 'success',
                    duration: 1500
                });
            } else {
                wx.showToast({
                    title: result.result.message || '操作失败',
                    icon: 'none',
                    duration: 2000
                });
            }

        } catch (error) {
            wx.hideLoading();
            console.error('切换收藏状态失败:', error);
            wx.showToast({
                title: '网络异常，请重试',
                icon: 'none',
                duration: 2000
            });
        }
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

    // 字幕设置 - 使用弹窗选择
    onSubtitleSettings() {
        const { subtitleMode } = this.data;
        const modes = ['both', 'en', 'zh'];
        const modeNames = ['双语模式', '仅英文', '仅中文'];
        const currentIndex = modes.indexOf(subtitleMode);

        wx.showActionSheet({
            itemList: modeNames,
            success: (res) => {
                if (res.tapIndex !== currentIndex) {
                    const newMode = modes[res.tapIndex];
                    this.setData({ subtitleMode: newMode });

                    wx.showToast({
                        title: modeNames[res.tapIndex],
                        icon: 'none',
                        duration: 1000
                    });
                }
            }
        });
    },

    // 播放速度控制 - 使用弹窗选择
    onSpeedChange() {
        const { playSpeed, speedOptions } = this.data;
        const options = speedOptions.map(speed => `${speed}x`);
        const currentIndex = speedOptions.indexOf(playSpeed);

        wx.showActionSheet({
            itemList: options,
            success: (res) => {
                if (res.tapIndex !== currentIndex) {
                    const newSpeed = speedOptions[res.tapIndex];
                    this.setData({ playSpeed: newSpeed });

                    // 如果音频对象已存在，立即应用速度
                    if (this.audioContext) {
                        this.audioContext.playbackRate = newSpeed;
                    }

                    wx.showToast({
                        title: `播放速度: ${newSpeed}x`,
                        icon: 'none',
                        duration: 1000
                    });
                }
            }
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
                console.log('学习进度更新成功');
            } else {
                console.error('学习进度更新失败:', result.result.message);
            }

        } catch (error) {
            console.error('更新学习进度异常:', error);
        }
    }
});