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
        
        // 触摸相关
        touchStartX: 0,
        touchStartY: 0,
        currentSlideIndex: -1,
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

            if (result.result.success) {
                const words = result.result.data.map(word => ({
                    ...word,
                    isExpanded: false,
                    isLearned: false,
                    isReviewed: false,
                    showActions: false
                }));

                this.setData({
                    words: words,
                    loading: false
                });
            } else {
                console.error('获取单词列表失败:', result.result.message);
                wx.showToast({
                    title: '加载失败',
                    icon: 'none'
                });
                this.setData({ loading: false });
            }
        } catch (error) {
            console.error('加载单词数据错误:', error);
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

    // 逾期单词展开/收起
    onToggleExpand(e) {
        const { index } = e.currentTarget.dataset;
        const { words } = this.data;
        
        // 收起其他展开的单词
        words.forEach((word, idx) => {
            if (idx !== index) {
                word.isExpanded = false;
            }
        });
        
        // 切换当前单词的展开状态
        words[index].isExpanded = !words[index].isExpanded;
        
        this.setData({ words });
    },


    // 开始学习新单词
    async startLearning(index) {
        try {
            const word = this.data.words[index];
            
            // 调用云函数更新学习记录
            const result = await wx.cloud.callFunction({
                name: 'wordStudy',
                data: {
                    action: 'updateWordRecord',
                    wordId: word.id,
                    actionType: 'start_learning'
                }
            });

            if (result.result.success) {
                // 更新UI状态：移除遮罩，标记为已学习
                const words = [...this.data.words];
                words[index].isLearned = true;
                words[index].isExpanded = true; // 移除遮罩
                
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

    // 处理逾期单词
    async onHandleOverdue(e) {
        const { index, action } = e.currentTarget.dataset;
        const word = this.data.words[index];
        
        try {
            // TODO: 调用云函数更新逾期单词记录
            // await this.updateOverdueWord(word.id, action);
            
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
        } catch (error) {
            console.error('处理逾期单词失败:', error);
            wx.showToast({
                title: '操作失败',
                icon: 'none'
            });
        }
    },

    // 复习单词相关的触摸事件
    onTouchStart(e) {
        if (this.data.wordType !== 'review') return;
        
        this.setData({
            touchStartX: e.touches[0].clientX,
            touchStartY: e.touches[0].clientY
        });
    },

    onTouchMove(e) {
        if (this.data.wordType !== 'review') return;
        
        const { touchStartX, touchStartY } = this.data;
        const touchMoveX = e.touches[0].clientX;
        const touchMoveY = e.touches[0].clientY;
        
        const deltaX = touchMoveX - touchStartX;
        const deltaY = touchMoveY - touchStartY;
        
        // 水平滑动距离大于垂直滑动距离且大于30px时触发
        if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 30) {
            const { index } = e.currentTarget.dataset;
            if (deltaX < 0) { // 左滑
                this.showSlideActions(index);
            }
        }
    },

    onTouchEnd(e) {
        if (this.data.wordType !== 'review') return;
        // 触摸结束处理
    },

    // 显示滑动操作按钮
    showSlideActions(index) {
        const words = [...this.data.words];
        
        // 隐藏其他单词的操作按钮
        words.forEach((word, idx) => {
            if (idx !== index) {
                word.showActions = false;
            }
        });
        
        // 显示当前单词的操作按钮
        words[index].showActions = true;
        
        this.setData({ 
            words,
            currentSlideIndex: index
        });
    },

    // 复习单词操作
    async onReviewWord(e) {
        const { index, action } = e.currentTarget.dataset;
        const word = this.data.words[index];
        
        try {
            // TODO: 调用云函数更新复习记录
            // await this.updateReviewRecord(word.id, action);
            
            // 更新UI状态
            const words = [...this.data.words];
            words[index].isReviewed = true;
            words[index].showActions = false;
            
            this.setData({ words });
            
            const actionText = {
                forgot: '忘记了',
                mastered: '记牢了'
            };
            
            wx.showToast({
                title: `已标记为${actionText[action]}`,
                icon: 'success'
            });
        } catch (error) {
            console.error('复习操作失败:', error);
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
        } else {
            // 其他类型：切换遮罩显示状态
            const words = [...this.data.words];
            words[index].isExpanded = !words[index].isExpanded;
            this.setData({ words });
        }
    }
});