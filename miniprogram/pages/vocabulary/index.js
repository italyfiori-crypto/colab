// vocabulary单词本页面逻辑
const vocabularyBookData = require('../../mock/vocabularyBookData.js');

Page({
    data: {
        currentDay: 'Day 1',
        currentDayKey: 'day1',
        currentTab: 'vocabulary',
        words: [],
        totalWords: 0,
        masteredWords: 0,
        progress: 0,
        availableDays: ['day1', 'day2', 'day3'],
        loading: true,
        // 显示模式：both(中英), chinese-mask(中文遮罩), english-mask(英文遮罩)
        displayMode: 'english-mask',
        showSettings: false,
        // 触摸相关
        touchStartX: 0,
        touchStartY: 0,
        currentSlideIndex: -1,
    },

    onLoad(options) {
        // 设置默认天数
        this.setData({
            currentDay: 'Day 1',
            currentDayKey: 'day1',
            displayMode: wx.getStorageSync('displayMode') || 'both'
        });

        // 加载单词数据
        this.loadVocabularyData('day1');

        // 设置导航栏标题
        wx.setNavigationBarTitle({
            title: '单词本'
        });
    },

    // 加载单词数据
    loadVocabularyData(dayKey) {
        try {
            const data = vocabularyBookData[dayKey];

            if (data) {
                // 为每个单词添加展开状态和学习状态
                const words = data.words.map(word => ({
                    ...word,
                    isExpanded: false,
                    isLearned: word.isLearned || false,
                    showActions: false
                }));

                this.setData({
                    words: words,
                    totalWords: data.totalWords,
                    masteredWords: data.masteredWords,
                    progress: data.progress,
                    loading: false
                });
            } else {
                this.setData({
                    words: [],
                    loading: false
                });

                wx.showToast({
                    title: '暂无单词数据',
                    icon: 'none',
                    duration: 2000
                });
            }
        } catch (error) {
            console.error('加载单词数据失败:', error);
            this.setData({
                loading: false
            });

            wx.showToast({
                title: '加载失败',
                icon: 'error',
                duration: 2000
            });
        }
    },

    // 上一天
    onPrevDay() {
        const currentIndex = this.data.availableDays.indexOf(this.data.currentDayKey);
        if (currentIndex > 0) {
            const prevDayKey = this.data.availableDays[currentIndex - 1];
            const prevDayNumber = currentIndex;
            this.setData({
                currentDay: `Day ${prevDayNumber}`,
                currentDayKey: prevDayKey
            });
            this.loadVocabularyData(prevDayKey);
        } else {
            wx.showToast({
                title: '已经是第一天了',
                icon: 'none',
                duration: 1000
            });
        }
    },

    // 下一天
    onNextDay() {
        const currentIndex = this.data.availableDays.indexOf(this.data.currentDayKey);
        if (currentIndex < this.data.availableDays.length - 1) {
            const nextDayKey = this.data.availableDays[currentIndex + 1];
            const nextDayNumber = currentIndex + 2;
            this.setData({
                currentDay: `Day ${nextDayNumber}`,
                currentDayKey: nextDayKey
            });
            this.loadVocabularyData(nextDayKey);
        } else {
            wx.showToast({
                title: '已经是最后一天了',
                icon: 'none',
                duration: 1000
            });
        }
    },

    // 显示设置弹窗
    onShowSettings() {
        this.setData({
            showSettings: true
        });
    },

    // 隐藏设置弹窗
    onHideSettings() {
        this.setData({
            showSettings: false
        });
    },

    // 切换显示模式
    onChangeDisplayMode(e) {
        const mode = e.currentTarget.dataset.mode;
        this.setData({
            displayMode: mode
        });

        // 保存到本地存储
        wx.setStorageSync('displayMode', mode);

        // 隐藏弹窗
        this.onHideSettings();

        // 重置所有单词的展开状态
        const words = this.data.words.map(word => ({
            ...word,
            isExpanded: false
        }));
        this.setData({
            words: words
        });

        wx.showToast({
            title: `已切换到${mode === 'both' ? '中英模式' : mode === 'chinese-mask' ? '中文遮罩模式' : '英文遮罩模式'}`,
            icon: 'none',
            duration: 1500
        });
    },

    // 遮罩点击事件
    onToggleMask(e) {
        const index = parseInt(e.currentTarget.dataset.index);
        if (index >= 0) {
            const words = this.data.words;
            words[index].isExpanded = !words[index].isExpanded;

            this.setData({
                words: words
            });
        }
    },

    // 单词点击事件 - 用于学习状态切换
    onWordTap(e) {
        const index = parseInt(e.currentTarget.dataset.index);
        if (index >= 0) {
            const words = this.data.words;
            const word = words[index];

            // 只有在显示模式为both或者遮罩已展开时，才能标记为已学习
            if (this.data.displayMode === 'both' || word.isExpanded) {
                words[index].isLearned = true;

                this.setData({
                    words: words
                });
            }
        }
    },

    // 触摸开始
    onTouchStart(e) {
        this.setData({
            touchStartX: e.touches[0].clientX,
            touchStartY: e.touches[0].clientY
        });
    },

    // 触摸移动
    onTouchMove(e) {
        const deltaX = e.touches[0].clientX - this.data.touchStartX;
        const deltaY = e.touches[0].clientY - this.data.touchStartY;

        // 判断是否为左滑手势（水平距离大于50，垂直距离小于100）
        if (Math.abs(deltaX) > 50 && Math.abs(deltaY) < 100 && deltaX < 0) {
            // 左滑操作
            const index = this.getCurrentTouchIndex(e);
            if (index >= 0 && index !== this.data.currentSlideIndex) {
                this.showSlideActions(index);
            }
        }
    },

    // 触摸结束
    onTouchEnd(e) {
        // 重置触摸数据
        this.setData({
            touchStartX: 0,
            touchStartY: 0
        });
    },

    // 获取当前触摸的单词索引
    getCurrentTouchIndex(e) {
        const dataset = e.currentTarget.dataset;
        return dataset.index ? parseInt(dataset.index) : -1;
    },

    // 显示滑动操作按钮
    showSlideActions(index) {
        // 隐藏其他所有的滑动按钮
        const words = this.data.words.map((word, i) => ({
            ...word,
            showActions: i === index
        }));

        this.setData({
            words: words,
            currentSlideIndex: index
        });
    },

    // 隐藏所有滑动操作按钮
    hideAllSlideActions() {
        const words = this.data.words.map(word => ({
            ...word,
            showActions: false
        }));

        this.setData({
            words: words,
            currentSlideIndex: -1
        });
    },

    // 标记为已掌握
    onMarkMastered(e) {
        const index = parseInt(e.currentTarget.dataset.index);
        if (index >= 0) {
            const words = this.data.words;
            words[index].status = 'mastered';
            words[index].isLearned = true;
            words[index].showActions = false;

            this.setData({
                words: words,
                currentSlideIndex: -1
            });

            wx.showToast({
                title: '已标记为掌握',
                icon: 'success',
                duration: 1000
            });
        }
    },

    // 标记为不熟悉
    onMarkUnfamiliar(e) {
        const index = parseInt(e.currentTarget.dataset.index);
        if (index >= 0) {
            const words = this.data.words;
            words[index].status = 'learning';
            words[index].isLearned = false;
            words[index].showActions = false;

            this.setData({
                words: words,
                currentSlideIndex: -1
            });

            wx.showToast({
                title: '已标记为不熟悉',
                icon: 'none',
                duration: 1000
            });
        }
    },

    // 删除单词
    onDeleteWord(e) {
        const index = parseInt(e.currentTarget.dataset.index);
        if (index >= 0) {
            wx.showModal({
                title: '确认删除',
                content: '确定要删除这个单词吗？',
                success: (res) => {
                    if (res.confirm) {
                        const words = this.data.words;
                        words.splice(index, 1);

                        this.setData({
                            words: words,
                            currentSlideIndex: -1,
                            totalWords: words.length
                        });

                        wx.showToast({
                            title: '删除成功',
                            icon: 'success',
                            duration: 1000
                        });
                    }
                }
            });
        }
    },

    // 底部导航标签点击处理
    onTabTap(e) {
        const tab = e.currentTarget.dataset.tab;

        this.setData({
            currentTab: tab
        });

        // 根据不同标签执行不同操作
        switch (tab) {
            case 'home':
                wx.switchTab({
                    url: '/pages/home/index'
                });
                break;
            case 'vocabulary':
                // 当前就是单词本页面，不需要操作
                break;
            case 'profile':
                wx.showToast({
                    title: '功能开发中...',
                    icon: 'none',
                    duration: 1500
                });
                break;
        }
    },

    // 页面分享
    onShareAppMessage() {
        return {
            title: `${this.data.currentDay} - 单词学习`,
            path: `/pages/vocabulary/index`,
            imageUrl: ''
        };
    },

    // 分享到朋友圈
    onShareTimeline() {
        return {
            title: `${this.data.currentDay} - 单词学习`,
            query: '',
            imageUrl: ''
        };
    },

    // 页面显示时的处理
    onShow() {
        this.hideAllSlideActions();
    },

    // 页面隐藏时的处理
    onHide() {
        this.hideAllSlideActions();
    },

    // 页面卸载时的处理
    onUnload() {
        // 页面卸载时的清理工作
    },

    // 下拉刷新
    onPullDownRefresh() {
        // 重新加载数据
        this.loadVocabularyData(this.data.currentDayKey);

        // 停止下拉刷新
        setTimeout(() => {
            wx.stopPullDownRefresh();
        }, 1000);
    }
});