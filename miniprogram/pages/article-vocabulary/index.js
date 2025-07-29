// article-vocabulary页面逻辑
const vocabularyData = require('../../mock/vocabularyData.js');

Page({
    data: {
        articleId: '',
        articleTitle: '',
        decodeTitle: '',
        words: [],
        totalWords: 0,
        masteredWords: 0,
        progress: 0,
        statusBarHeight: 44, // 状态栏高度，默认值
        contentPaddingTop: 98, // 内容区域顶部间距
        loading: true,
    },

    onLoad(options) {
        // 获取状态栏高度
        this.getSystemInfo();

        // 获取页面参数
        const { articleId, title } = options;

        if (articleId) {
            this.setData({
                articleId: articleId,
                articleTitle: title || '文章',
                decodeTitle: decodeURIComponent(title || '文章')
            });

            // 加载单词数据
            this.loadVocabularyData(articleId);
        } else {
            // 如果没有传入文章ID，显示错误或返回上一页
            wx.showToast({
                title: '参数错误',
                icon: 'error',
                duration: 2000
            });

            setTimeout(() => {
                wx.navigateBack();
            }, 2000);
        }

        // 设置自定义导航栏标题
        wx.setNavigationBarTitle({
            title: `${decodeURIComponent(this.data.articleTitle)} 单词`
        });
    },

    // 获取系统信息，主要是状态栏高度
    getSystemInfo() {
        const systemInfo = wx.getSystemInfoSync();
        const statusBarHeight = systemInfo.statusBarHeight || 44;
        const navbarHeight = 44; // 88rpx转px大约44px
        const paddingTop = 10; // 额外间距

        this.setData({
            statusBarHeight: statusBarHeight,
            contentPaddingTop: statusBarHeight + navbarHeight + paddingTop
        });
    },

    // 加载单词数据
    loadVocabularyData(articleId) {
        try {
            const data = vocabularyData[articleId];

            if (data) {
                this.setData({
                    words: data.words,
                    totalWords: data.totalWords,
                    masteredWords: data.masteredWords,
                    progress: data.progress,
                    loading: false
                });
            } else {
                // 没有找到对应的单词数据
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

    // 返回上一页
    onBack() {
        wx.navigateBack();
    },

    // 单词点击事件
    onWordTap(e) {
        console.log('单词项被点击', e);
        const word = e.currentTarget.dataset.word;
        console.log('点击单词:', word);

        // 这里可以添加单词详情页面跳转或其他交互
        // 暂时显示提示
        wx.showToast({
            title: `查看 ${word.word} 详情`,
            icon: 'none',
            duration: 1000
        });
    },

    // 切换收藏状态
    onToggleFavorite(e) {
        const wordId = parseInt(e.currentTarget.dataset.id);
        if (!wordId) {
            console.error('没有获取到单词ID');
            return;
        }
        const words = this.data.words;

        // 找到对应的单词并切换收藏状态
        const updatedWords = words.map(word => {
            if (word.id === wordId) {
                return {
                    ...word,
                    isFavorited: !word.isFavorited
                };
            }
            return word;
        });


        // 更新数据
        this.setData({
            words: updatedWords
        });
    },

    // 页面分享
    onShareAppMessage() {
        return {
            title: `${this.data.articleTitle} - 单词学习`,
            path: `/pages/article-vocabulary/index?articleId=${this.data.articleId}&title=${encodeURIComponent(this.data.articleTitle)}`,
            imageUrl: '' // 可以设置分享图片
        };
    },

    // 分享到朋友圈
    onShareTimeline() {
        return {
            title: `${this.data.articleTitle} - 单词学习`,
            query: `articleId=${this.data.articleId}&title=${encodeURIComponent(this.data.articleTitle)}`,
            imageUrl: '' // 可以设置分享图片
        };
    },

    // 页面显示时的处理
    onShow() {
        // 页面显示时的逻辑，比如刷新数据等
    },

    // 页面隐藏时的处理
    onHide() {
        // 页面隐藏时的逻辑
    },

    // 页面卸载时的处理
    onUnload() {
        // 页面卸载时的清理工作
    },

    // 下拉刷新
    onPullDownRefresh() {
        // 重新加载数据
        this.loadVocabularyData(this.data.articleId);

        // 停止下拉刷新
        setTimeout(() => {
            wx.stopPullDownRefresh();
        }, 1000);
    }
}); 