// home页面逻辑
const homeData = require('../../mock/homeData.js');

Page({
  data: {
    searchKeyword: '',
    recentBooks: [],
    categories: [],
    currentCategoryBooks: [],
    currentCategory: 'literature',
    currentTab: 'home'
  },

  onLoad() {
    this.loadData();
  },

  // 加载页面数据
  loadData() {
    const { recentBooks, categories, categoryBooks } = homeData;
    
    // 设置最近学习书籍
    this.setData({
      recentBooks: recentBooks,
      categories: categories,
      currentCategoryBooks: categoryBooks[this.data.currentCategory]
    });
  },

  // 搜索输入处理
  onSearchInput(e) {
    this.setData({
      searchKeyword: e.detail.value
    });
  },

  // 搜索确认处理
  onSearchConfirm(e) {
    const keyword = e.detail.value.trim();
    if (keyword) {
      // 这里可以实现搜索功能
      console.log('搜索关键词:', keyword);
      wx.showToast({
        title: `搜索: ${keyword}`,
        icon: 'none',
        duration: 1500
      });
    }
  },

  // 查看全部最近学习
  onViewAllRecent() {
    wx.showToast({
      title: '查看全部最近学习',
      icon: 'none',
      duration: 1500
    });
  },

  // 分类标签点击处理
  onCategoryTap(e) {
    const categoryId = e.currentTarget.dataset.category;
    
    // 更新分类状态
    const categories = this.data.categories.map(cat => ({
      ...cat,
      active: cat.id === categoryId
    }));

    // 获取对应分类的书籍数据
    const categoryBooks = homeData.categoryBooks[categoryId] || [];

    this.setData({
      categories: categories,
      currentCategory: categoryId,
      currentCategoryBooks: categoryBooks
    });
  },

  // 书籍点击处理
  onBookTap(e) {
    const book = e.currentTarget.dataset.book;
    console.log('点击书籍:', book);
    
    // 可以跳转到书籍详情页
    wx.showToast({
      title: `打开《${book.title}》`,
      icon: 'none',
      duration: 1500
    });
    
    // 示例：跳转到文章详情页
    // wx.navigateTo({
    //   url: `/pages/article-detail/index?bookId=${book.id}`
    // });
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
        // 当前就是首页，不需要操作
        break;
      case 'vocabulary':
        wx.showToast({
          title: '功能开发中...',
          icon: 'none',
          duration: 1500
        });
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

  // 页面显示时触发
  onShow() {
    // 确保当前标签页为首页
    this.setData({
      currentTab: 'home'
    });
  },

  // 下拉刷新
  onPullDownRefresh() {
    // 重新加载数据
    this.loadData();
    
    // 延迟关闭下拉刷新
    setTimeout(() => {
      wx.stopPullDownRefresh();
    }, 1000);
  },

  // 页面分享
  onShareAppMessage() {
    return {
      title: '英语学习 - 发现更多好书',
      path: '/pages/home/index'
    };
  },

  // 分享到朋友圈
  onShareTimeline() {
    return {
      title: '英语学习 - 发现更多好书'
    };
  }
});