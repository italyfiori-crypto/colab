// vocabulary单词本页面逻辑
Page({
    data: {
        // 页面类型: new(新学), review(复习), overdue(逾期)
        wordType: 'new',
        pageTitle: '新学单词',

        words: [],
        loading: true,

        // 显示模式：both(中英), chinese-mask(中文遮罩), english-mask(英文遮罩)
        displayMode: 'both',
        showSettings: false,

    },

    onLoad(options) {
        const { type = 'new' } = options;

        // 根据类型设置页面配置
        const pageConfig = {
            new: { title: '新学单词', navTitle: '新学单词' },
            review: { title: '复习单词', navTitle: '复习单词' },
            overdue: { title: '逾期单词', navTitle: '逾期单词' }
        };

        const config = pageConfig[type] || pageConfig.new;

        // 根据单词类型设置显示模式
        let displayMode = wx.getStorageSync('displayMode') || 'both';
        if (type === 'new') {
            displayMode = 'chinese-mask'; // 新学单词默认遮罩中文
        }

        this.setData({
            wordType: type,
            pageTitle: config.title,
            displayMode: displayMode
        });

        // 设置导航栏标题
        wx.setNavigationBarTitle({
            title: config.navTitle
        });

        // 加载对应类型的单词数据
        this.loadWordsByType(type);
    },

    // 根据类型加载单词数据
    async loadWordsByType(type) {
        try {
            console.log('🔄 [DEBUG] 开始加载单词列表:', {
                类型: type,
                时间: new Date().toISOString().split('T')[0]
            });

            this.setData({ loading: true });

            // 调用云函数获取对应类型的单词
            const result = await wx.cloud.callFunction({
                name: 'wordStudy',
                data: {
                    action: 'getWordList',
                    type: type,
                    limit: 50
                }
            });

            console.log('📥 [DEBUG] 云函数返回结果:', {
                成功: result.result.success,
                单词数量: result.result.data ? result.result.data.length : 0,
                完整结果: result.result
            });

            if (result.result.success) {
                const words = result.result.data.map(word => ({
                    ...word,
                    isExpanded: type === 'overdue' ? true : false,  // 逾期单词默认展开
                    isLearned: false,
                    isReviewed: false,
                    showActions: false
                }));

                console.log('✅ [DEBUG] 单词列表加载成功:', {
                    类型: type,
                    数量: words.length,
                    单词列表: words.map(w => ({ 单词: w.word, ID: w.id }))
                });

                this.setData({
                    words: words,
                    loading: false
                });
            } else {
                console.error('❌ [DEBUG] 获取单词列表失败:', {
                    错误信息: result.result.message,
                    完整结果: result.result
                });
                wx.showToast({
                    title: '加载失败',
                    icon: 'none'
                });
                this.setData({ loading: false });
            }
        } catch (error) {
            console.error('❌ [DEBUG] 加载单词数据异常:', {
                错误信息: error.message,
                错误详情: error,
                类型: type
            });
            wx.showToast({
                title: '加载失败',
                icon: 'none'
            });
            this.setData({ loading: false });
        }
    },

    // 新学单词点击事件
    onWordTap(e) {
        // 新学单词的点击现在通过遮罩处理，这里暂时保留空实现
    },



    // 开始学习新单词
    async startLearning(index) {
        try {
            const word = this.data.words[index];

            console.log('📖 [DEBUG] 开始学习新单词:', {
                单词: word.word,
                索引: index
            });

            // 调用云函数更新学习记录
            const result = await wx.cloud.callFunction({
                name: 'wordStudy',
                data: {
                    action: 'updateWordRecord',
                    word: word.word,
                    actionType: 'start'
                }
            });

            if (result.result.success) {
                // 只移除遮罩，显示单词内容，标记为已学习
                const words = [...this.data.words];
                words[index].isExpanded = true;  // 移除遮罩显示内容
                words[index].isLearned = true;   // 标记为已学习状态
                this.setData({ words });

                wx.showToast({
                    title: '开始学习',
                    icon: 'success'
                });
            } else {
                console.error('更新学习记录失败:', result.result.message);
                wx.showToast({
                    title: result.result.message || '操作失败',
                    icon: 'none'
                });
            }
        } catch (error) {
            console.error('开始学习失败:', error);
            wx.showToast({
                title: '操作失败',
                icon: 'none'
            });
        }
    },

    // 开始复习单词
    async startReviewing(index) {
        try {
            const word = this.data.words[index];

            console.log('📖 [DEBUG] 开始复习单词:', {
                单词: word.word,
                索引: index
            });

            // 调用云函数更新复习记录
            const result = await wx.cloud.callFunction({
                name: 'wordStudy',
                data: {
                    action: 'updateWordRecord',
                    word: word.word,
                    actionType: 'review'  // 默认复习成功
                }
            });

            if (result.result.success) {
                // 移除遮罩，显示单词内容，标记为已复习
                const words = [...this.data.words];
                words[index].isExpanded = true;  // 移除遮罩显示内容
                words[index].isReviewed = true;  // 标记为已复习状态
                this.setData({ words });

                wx.showToast({
                    title: '复习完成',
                    icon: 'success'
                });

                console.log('✅ [DEBUG] 复习单词成功:', {
                    单词: word.word,
                    剩余单词数: words.length
                });

                // 如果处理完所有复习单词
                if (words.filter(w => !w.isReviewed).length === 0) {
                    setTimeout(() => {
                        console.log('🎉 [DEBUG] 所有复习单词已完成');
                        wx.showToast({
                            title: '所有复习单词已完成！',
                            icon: 'success'
                        });
                    }, 500);
                }
            } else {
                console.error('❌ [DEBUG] 更新复习记录失败:', result.result.message);
                wx.showToast({
                    title: result.result.message || '操作失败',
                    icon: 'none'
                });
            }
        } catch (error) {
            console.error('❌ [DEBUG] 复习操作失败:', error);
            wx.showToast({
                title: '操作失败',
                icon: 'none'
            });
        }
    },

    // 处理逾期单词
    async onHandleOverdue(e) {
        const { index, action } = e.currentTarget.dataset;
        const word = this.data.words[index];

        try {
            // 映射到新的 actionType
            const actionTypeMap = {
                'remember': 'remember',
                'vague': 'vague', 
                'forgot': 'reset'
            };

            // 调用云函数更新逾期单词记录
            const result = await wx.cloud.callFunction({
                name: 'wordStudy',
                data: {
                    action: 'updateWordRecord',
                    word: word.word,
                    actionType: actionTypeMap[action]
                }
            });

            if (result.result.success) {
                // 从列表中移除该单词
                const words = this.data.words.filter((_, idx) => idx !== index);
                this.setData({ words });
                
                const actionText = {
                    remember: '还记得',
                    vague: '有点模糊',
                    forgot: '忘记了'
                };
                
                wx.showToast({
                    title: `已标记为${actionText[action]}`,
                    icon: 'success'
                });
                
                // 如果处理完所有逾期单词
                if (words.length === 0) {
                    setTimeout(() => {
                        wx.showToast({
                            title: '所有逾期单词已处理完成！',
                            icon: 'success'
                        });
                    }, 500);
                }
            } else {
                console.error('更新逾期单词记录失败:', result.result.message);
                wx.showToast({
                    title: result.result.message || '操作失败',
                    icon: 'none'
                });
            }
        } catch (error) {
            console.error('处理逾期单词失败:', error);
            wx.showToast({
                title: '操作失败',
                icon: 'none'
            });
        }
    },


    // 显示设置
    onShowSettings() {
        this.setData({ showSettings: true });
    },

    // 隐藏设置
    onHideSettings() {
        this.setData({ showSettings: false });
    },

    // 切换显示模式
    onChangeDisplayMode(e) {
        const { mode } = e.currentTarget.dataset;
        this.setData({
            displayMode: mode,
            showSettings: false
        });

        // 保存到本地存储
        wx.setStorageSync('displayMode', mode);
    },

    // 切换遮罩显示
    onToggleMask(e) {
        const { index } = e.currentTarget.dataset;
        const { wordType } = this.data;

        if (wordType === 'new') {
            // 新学单词：点击遮罩直接开始学习
            this.startLearning(index);
        } else if (wordType === 'review') {
            // 复习单词：点击遮罩直接完成复习
            this.startReviewing(index);
        } else {
            // 逾期单词：切换遮罩显示状态
            const words = [...this.data.words];
            words[index].isExpanded = !words[index].isExpanded;
            this.setData({ words });
        }
    }
});