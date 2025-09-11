// vocabulary单词本页面逻辑
const settingsUtils = require('../../utils/settingsUtils.js');

// 常量定义
const WORD_TYPE = {
    NEW: 'new',
    REVIEW: 'review',
    OVERDUE: 'overdue'
};

const DISPLAY_MODE = {
    BOTH: 'both',
    CHINESE_MASK: 'chinese-mask',
    ENGLISH_MASK: 'english-mask'
};

const PAGE_CONFIG = {
    [WORD_TYPE.NEW]: {
        title: '新学单词',
        navTitle: '新学单词',
        displayMode: DISPLAY_MODE.CHINESE_MASK
    },
    [WORD_TYPE.REVIEW]: {
        title: '复习单词',
        navTitle: '复习单词',
        displayMode: DISPLAY_MODE.CHINESE_MASK
    },
    [WORD_TYPE.OVERDUE]: {
        title: '逾期单词',
        navTitle: '逾期单词',
        displayMode: DISPLAY_MODE.BOTH
    }
};

// 错误处理配置
const ERROR_CONFIG = {
    NETWORK_ERROR: {
        title: '网络连接失败',
        message: '请检查网络连接后重试',
        canRetry: true
    },
    SERVER_ERROR: {
        title: '服务器异常',
        message: '服务暂时不可用，请稍后重试',
        canRetry: true
    },
    DATA_ERROR: {
        title: '数据加载失败',
        message: '数据格式异常，请联系客服',
        canRetry: false
    },
    UNKNOWN_ERROR: {
        title: '操作失败',
        message: '发生未知错误，请重试',
        canRetry: true
    }
};

const MAX_RETRY_COUNT = 3;

Page({
    data: {
        // 页面类型: new(新学), review(复习), overdue(逾期)
        wordType: 'new',
        pageTitle: '新学单词',

        words: [],
        loading: true,
        refreshing: false,

        // 显示模式：both(中英), chinese-mask(中文遮罩), english-mask(英文遮罩)
        displayMode: 'both',

        // 播放速度
        playSpeed: 1.0,

        // 用户设置
        userSettings: {}
    },

    /**
     * 页面加载时的初始化
     * @param {Object} options - 页面参数
     */
    async onLoad(options) {
        const { type = WORD_TYPE.NEW } = options;
        const config = PAGE_CONFIG[type] || PAGE_CONFIG[WORD_TYPE.NEW];

        // 加载用户设置
        await this.loadUserSettings();
        this.initializePage(type, config);
        this.loadWordsByType(type);
    },

    /**
     * 初始化页面配置
     * @param {string} type - 单词类型
     * @param {Object} config - 页面配置
     */
    /**
     * 加载用户设置
     */
    async loadUserSettings() {
        const userInfo = await settingsUtils.getCompleteUserInfo();
        // 从用户设置中获取播放速度，默认为1.0
        const playSpeed = userInfo.learning_settings?.playback_speed || 1.0;
        this.setData({ 
            userSettings: userInfo,
            playSpeed: playSpeed
        });
    },

    initializePage(type, config) {
        this.setData({
            wordType: type,
            pageTitle: config.title,
            displayMode: config.displayMode
        });

        wx.setNavigationBarTitle({
            title: config.navTitle
        });
    },

    /**
     * 根据类型加载单词数据（支持重试）
     * @param {string} type - 单词类型
     * @param {number} retryCount - 重试次数
     */
    async loadWordsByType(type, retryCount = 0) {
        try {
            console.log('🔄 [DEBUG] 开始加载单词列表:', {
                类型: type,
                重试次数: retryCount
            });

            this.setData({ loading: true });

            const result = await this.fetchWordList(type);

            if (result.success) {
                this.handleLoadSuccess(result.data, type);
            } else {
                this.handleLoadError(result.message, type, retryCount);
            }
        } catch (error) {
            this.handleLoadError(error.message, type, retryCount);
        }
    },

    /**
     * 调用云函数获取单词列表
     * @param {string} type - 单词类型
     * @returns {Promise<Object>} 云函数结果
     */
    async fetchWordList(type) {
        const { userSettings } = this.data;
        const learningSettings = userSettings.learning_settings || {};
        
        // 准备云函数参数
        const cloudFunctionData = {
            action: 'getWordList',
            type: type,
            limit: 50
        };

        // 根据单词类型添加特定参数
        if (type === 'new') {
            // 新学单词需要每日上限参数和排序参数
            cloudFunctionData.dailyWordLimit = learningSettings.daily_word_limit;
            cloudFunctionData.sortOrder = settingsUtils.mapNewWordSortOrder(learningSettings.new_word_sort || '优先新词');
        } else if (type === 'review' || type === 'overdue') {
            // 复习和逾期单词需要排序参数
            cloudFunctionData.sortOrder = settingsUtils.mapReviewSortOrder('优先新词'); // 暂时使用固定值，因为已移除复习排序设置
        }

        console.log('☁️ [DEBUG] 调用云函数参数:', cloudFunctionData);
        console.log('📋 [DEBUG] 用户设置详情:', {
            learningSettings: learningSettings,
            daily_word_limit: learningSettings.daily_word_limit,
            new_word_sort: learningSettings.new_word_sort,
            传递的dailyWordLimit: cloudFunctionData.dailyWordLimit,
            传递的sortOrder: cloudFunctionData.sortOrder
        });

        const result = await wx.cloud.callFunction({
            name: 'wordStudy',
            data: cloudFunctionData
        });

        console.log('📥 [DEBUG] 云函数返回结果:', {
            成功: result.result.success,
            result: result,
            单词数量: result.result.data ? result.result.data.length : 0
        });

        return result.result;
    },

    /**
     * 处理加载成功的情况
     * @param {Array} wordsData - 单词数据
     * @param {string} type - 单词类型
     */
    handleLoadSuccess(wordsData, type) {
        const { userSettings } = this.data;
        const voiceType = userSettings.learning_settings?.voice_type || '美式发音';
        
        const words = wordsData.map(word => {
            // 根据用户设置选择音标和音频
            let displayPhonetic, audioUrl;
            if (voiceType === '美式发音') {
                displayPhonetic = word.phonetic_us || word.phonetic_uk || '';
                audioUrl = word.audio_url_us || word.audio_url_uk || '';
            } else {
                displayPhonetic = word.phonetic_uk || word.phonetic_us || '';
                audioUrl = word.audio_url_uk || word.audio_url_us || '';
            }
            
            return {
                ...word,
                displayPhonetic,
                audioUrl,
                isExpanded: type === WORD_TYPE.OVERDUE, // 逾期单词默认展开
                isLearned: false,
                isReviewed: false
            };
        });

        console.log('✅ [DEBUG] 单词列表加载成功:', {
            类型: type,
            数量: words.length,
            首个单词: words[0]?.word || '无',
            音频偏好: voiceType
        });

        this.setData({
            words: words,
            loading: false
        });
    },

    /**
     * 处理加载错误的情况
     * @param {string} errorMessage - 错误信息
     * @param {string} type - 单词类型
     * @param {number} retryCount - 当前重试次数
     */
    handleLoadError(errorMessage, type, retryCount) {
        console.error('❌ [DEBUG] 加载单词数据失败:', {
            错误信息: errorMessage,
            类型: type,
            重试次数: retryCount
        });

        const errorType = this.determineErrorType(errorMessage);
        const errorConfig = ERROR_CONFIG[errorType];

        if (errorConfig.canRetry && retryCount < MAX_RETRY_COUNT) {
            // 可以重试，延迟后重试
            setTimeout(() => {
                this.loadWordsByType(type, retryCount + 1);
            }, 1000 * (retryCount + 1)); // 递增延迟
        } else {
            // 不能重试或达到最大重试次数
            this.setData({ loading: false });
            wx.showToast({
                title: errorConfig.title,
                icon: 'none',
                duration: 3000
            });
        }
    },

    /**
     * 根据错误信息确定错误类型
     * @param {string} errorMessage - 错误信息
     * @returns {string} 错误类型
     */
    determineErrorType(errorMessage) {
        if (errorMessage.includes('网络') || errorMessage.includes('network')) {
            return 'NETWORK_ERROR';
        } else if (errorMessage.includes('服务器') || errorMessage.includes('server')) {
            return 'SERVER_ERROR';
        } else if (errorMessage.includes('数据') || errorMessage.includes('data')) {
            return 'DATA_ERROR';
        } else {
            return 'UNKNOWN_ERROR';
        }
    },




    /**
     * 开始学习新单词
     * @param {number} index - 单词在列表中的索引
     */
    async startLearning(index) {
        const word = this.data.words[index];

        if (!word) {
            console.error('❌ 单词不存在:', index);
            return;
        }

        try {
            console.log('📖 [DEBUG] 开始学习新单词:', {
                单词: word.word,
                索引: index
            });

            const result = await this.updateWordRecord(word.word_id, 'start');

            if (result.success) {
                this.updateWordState(index, {
                    isExpanded: true,
                    isLearned: true
                });
            } else {
                this.showErrorToast(result.message || '学习失败');
            }
        } catch (error) {
            console.error('开始学习失败:', error);
            this.showErrorToast('操作失败');
        }
    },

    /**
     * 开始复习单词
     * @param {number} index - 单词在列表中的索引
     */
    async startReviewing(index) {
        const word = this.data.words[index];

        if (!word) {
            console.error('❌ 单词不存在:', index);
            return;
        }

        try {
            console.log('📖 [DEBUG] 开始复习单词:', {
                单词: word.word,
                索引: index
            });

            const result = await this.updateWordRecord(word.word_id, 'review');

            if (result.success) {
                this.updateWordState(index, {
                    isExpanded: true,
                    isReviewed: true
                });

                console.log('✅ [DEBUG] 复习单词成功:', {
                    单词: word.word
                });

                // 检查是否完成所有复习
                this.checkReviewCompletion();
            } else {
                this.showErrorToast(result.message || '复习失败');
            }
        } catch (error) {
            console.error('❌ [DEBUG] 复习操作失败:', error);
            this.showErrorToast('操作失败');
        }
    },

    /**
     * 检查复习任务是否完成
     */
    checkReviewCompletion() {
        const unreviewedWords = this.data.words.filter(w => !w.isReviewed);

        if (unreviewedWords.length === 0) {
            setTimeout(() => {
                wx.showToast({
                    title: '所有复习单词已完成！',
                    icon: 'success',
                    duration: 2000
                });
            }, 500);
        }
    },

    /**
     * 处理逾期单词操作
     * @param {Object} e - 事件对象
     */
    async onHandleOverdue(e) {
        const { index, action } = e.currentTarget.dataset;
        const word = this.data.words[index];

        if (!word) {
            console.error('❌ 单词不存在:', index);
            return;
        }

        try {
            console.log('🔄 [DEBUG] 处理逾期单词:', {
                单词: word.word,
                操作: action,
                索引: index
            });

            const result = await this.updateWordRecord(word.word_id, action);

            if (result.success) {
                this.handleOverdueSuccess(index, action);
            } else {
                this.showErrorToast(result.message || '操作失败');
            }
        } catch (error) {
            console.error('❌ [DEBUG] 处理逾期单词失败:', error);
            this.showErrorToast('操作失败');
        }
    },

    /**
     * 处理逾期单词成功的回调
     * @param {number} index - 单词索引
     * @param {string} action - 操作类型
     */
    handleOverdueSuccess(index, action) {
        // 添加移除动画效果
        this.updateWordState(index, { removing: true });

        const actionText = {
            remember: '还记得',
            vague: '有点模糊',
            forgot: '忘记了'
        };

        wx.showToast({
            title: `已标记为${actionText[action]}`,
            icon: 'success'
        });

        // 延迟移除单词，让动画完成
        setTimeout(() => {
            this.removeWordFromList(index);
        }, 400);
    },

    /**
     * 从列表中移除单词
     * @param {number} index - 要移除的单词索引
     */
    removeWordFromList(index) {
        const updatedWords = this.data.words.filter((_, idx) => idx !== index);
        this.setData({ words: updatedWords });

        // 检查是否完成所有逾期单词处理
        if (updatedWords.length === 0) {
            setTimeout(() => {
                wx.showToast({
                    title: '所有逾期单词已处理完成！',
                    icon: 'success',
                    duration: 2000
                });
            }, 300);
        }
    },

    /**
     * 下拉刷新处理
     */
    async onRefresh() {
        console.log('🔄 [DEBUG] 用户触发下拉刷新');
        this.setData({ refreshing: true });

        try {
            // 重新加载当前类型的单词数据
            await this.loadWordsByType(this.data.wordType);

            wx.showToast({
                title: '刷新成功',
                icon: 'success',
                duration: 1500
            });
        } catch (error) {
            console.error('❌ [DEBUG] 下拉刷新失败:', error);
            this.showErrorToast('刷新失败');
        } finally {
            // 停止刷新状态
            this.setData({ refreshing: false });
        }
    },

    /**
     * 处理遮罩切换事件（从word-list组件传递过来）
     * @param {Object} e - 事件对象
     */
    onMaskToggle(e) {
        const { index, words } = e.detail;
        this.handleMaskInteraction(index);
        this.setData({ words });
    },

    /**
     * 统一的遮罩交互处理逻辑
     * @param {number} index - 单词索引
     */
    handleMaskInteraction(index) {
        const { wordType } = this.data;

        switch (wordType) {
            case 'new':
                this.startLearning(index);
                break;
            case 'review':
                this.startReviewing(index);
                break;
            case 'overdue':
                this.toggleOverdueExpansion(index);
                break;
            default:
                console.warn('未知的单词类型:', wordType);
        }
    },

    /**
     * 切换逾期单词的展开状态
     * @param {number} index - 单词索引
     */
    toggleOverdueExpansion(index) {
        const words = [...this.data.words];
        words[index].isExpanded = !words[index].isExpanded;
        this.setData({ words });
    },

    /**
     * 统一的单词记录更新方法
     * @param {string} wordId - 单词ID
     * @param {string} actionType - 操作类型
     * @returns {Promise<Object>} 更新结果
     */
    async updateWordRecord(wordId, actionType) {
        const result = await wx.cloud.callFunction({
            name: 'wordStudy',
            data: {
                action: 'updateWordRecord',
                word_id: wordId,
                actionType: actionType
            }
        });
        return result.result;
    },

    /**
     * 更新单词状态（性能优化版本）
     * @param {number} index - 单词索引
     * @param {Object} updates - 要更新的状态
     */
    updateWordState(index, updates) {
        const updateData = {};
        Object.keys(updates).forEach(key => {
            updateData[`words[${index}].${key}`] = updates[key];
        });
        this.setData(updateData);
    },


    /**
     * 单词点击事件处理（来自word-list组件）
     * @param {Object} e - 事件对象
     */
    onWordTap(e) {
        const { word, index } = e.detail;
        console.log('🔊 [DEBUG] 单词点击:', {
            word: word.word,
            index: index,
            hasAudioUrl: !!word.audioUrl,
            audioUrl: word.audioUrl
        });
        // 音频播放已经在word-list组件中处理，这里可以添加其他逻辑
    },

    /**
     * 显示错误提示
     * @param {string} message - 错误消息
     */
    showErrorToast(message) {
        wx.showToast({
            title: message,
            icon: 'none',
            duration: 2500
        });
    }
});