// book-detail页面逻辑
const bookDetailData = require('../../mock/bookDetailData.js');

Page({
  data: {
    statusBarHeight: 44, // 状态栏高度，会在onLoad中动态获取
    bookInfo: {},
    chapters: [],
    filterOptions: [],
    currentFilter: 'all',
    currentFilterText: '全部章节',
    showFilterModal: false,
  },

  onLoad(options) {
    // 获取状态栏高度
    const systemInfo = wx.getSystemInfoSync();
    this.setData({
      statusBarHeight: systemInfo.statusBarHeight || 44
    });

    // 获取传入的书籍ID（如果有）
    const bookId = options.bookId || 1;

    // 加载书籍详情数据
    this.loadBookDetail(bookId);
  },

  // 加载书籍详情数据
  loadBookDetail(bookId) {
    // 这里可以根据bookId从不同数据源加载，现在使用mock数据
    const { bookInfo, chapters, filterOptions } = bookDetailData;

    this.setData({
      bookInfo: bookInfo,
      chapters: chapters,
      filterOptions: filterOptions
    });
  },

  // 章节点击
  onChapterTap(e) {
    const chapter = e.currentTarget.dataset.chapter;

    if (chapter.status === 'locked') {
      wx.showToast({
        title: '请先完成前面的章节',
        icon: 'none',
        duration: 1500
      });
      return;
    }

    // 跳转到learning页面
    wx.navigateTo({
      url: `/pages/article-detail/index?chapterId=${chapter.id}&bookId=${this.data.bookInfo.id}&chapterTitle=${encodeURIComponent(chapter.title)}`
    });
  },


  // 显示筛选器模态框
  onShowFilterModal() {
    this.setData({
      showFilterModal: true
    });
  },

  // 隐藏筛选器模态框
  onHideFilterModal() {
    this.setData({
      showFilterModal: false
    });
  },

  // 筛选器选择
  onFilterChange(e) {
    const filterValue = e.currentTarget.dataset.value;
    const filterOption = this.data.filterOptions.find(option => option.value === filterValue);

    let filteredChapters = this.data.chapters;
    if (filterValue !== 'all') {
      filteredChapters = this.data.chapters.filter(chapter => chapter.status === filterValue);
    }

    this.setData({
      currentFilter: filterValue,
      currentFilterText: filterOption.label,
      chapters: filteredChapters,
      showFilterModal: false
    });
  },

  // 页面显示时
  onShow() {
    // 可以在这里刷新数据或更新状态
  },

  // 下拉刷新
  onPullDownRefresh() {
    // 重新加载数据
    this.loadBookDetail(this.data.bookInfo.id);

    setTimeout(() => {
      wx.stopPullDownRefresh();
    }, 1000);
  },

  // 页面分享
  onShareAppMessage() {
    return {
      title: `《${this.data.bookInfo.title}》- 一起来学习英语吧`,
      path: `/pages/book-detail/index?bookId=${this.data.bookInfo.id}`,
      imageUrl: this.data.bookInfo.cover
    };
  },

  // 分享到朋友圈
  onShareTimeline() {
    return {
      title: `正在学习《${this.data.bookInfo.title}》`,
      imageUrl: this.data.bookInfo.cover
    };
  }
});