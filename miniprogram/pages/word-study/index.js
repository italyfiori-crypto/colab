// 单词本入口页面逻辑
Page({
  data: {
    // 统计数据
    totalWords: 0,
    studiedToday: 0,
    masteredWords: 0,
    
    // 各类单词数量
    newWordsCount: 0,
    reviewWordsCount: 0,
    overdueWordsCount: 0,
    
    // 页面状态
    loading: true,
  },

  onLoad(options) {
    wx.setNavigationBarTitle({
      title: '单词学习'
    });
    this.loadStudyStats();
  },

  onShow() {
    // 每次显示时刷新数据
    this.loadStudyStats();
  },

  // 加载学习统计数据
  async loadStudyStats() {
    try {
      this.setData({ loading: true });

      // 调用云函数获取学习统计
      const result = await wx.cloud.callFunction({
        name: 'wordStudy',
        data: {
          action: 'getStudyStats'
        }
      });

      if (result.result.success) {
        const stats = result.result.data;
        this.setData({
          totalWords: stats.totalWords,
          studiedToday: stats.studiedToday,
          masteredWords: stats.masteredWords,
          newWordsCount: stats.newWordsCount,
          reviewWordsCount: stats.reviewWordsCount,
          overdueWordsCount: stats.overdueWordsCount,
          loading: false
        });
      } else {
        console.error('获取学习统计失败:', result.result.message);
        wx.showToast({
          title: '加载失败',
          icon: 'none'
        });
        this.setData({ loading: false });
      }
    } catch (error) {
      console.error('加载学习统计错误:', error);
      wx.showToast({
        title: '加载失败',
        icon: 'none'
      });
      this.setData({ loading: false });
    }
  },

  // 进入新学单词页面
  onEnterNewWords() {
    wx.navigateTo({
      url: '/pages/vocabulary/index?type=new'
    });
  },

  // 进入复习单词页面
  onEnterReviewWords() {
    wx.navigateTo({
      url: '/pages/vocabulary/index?type=review'
    });
  },

  // 进入逾期单词页面
  onEnterOverdueWords() {
    wx.navigateTo({
      url: '/pages/vocabulary/index?type=overdue'
    });
  },

  // 显示学习设置
  onShowSettings() {
    wx.showToast({
      title: '设置功能开发中',
      icon: 'none'
    });
  }
});