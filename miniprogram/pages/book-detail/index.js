// book-detail页面逻辑
Page({
  data: {
    statusBarHeight: 44, // 状态栏高度，会在onLoad中动态获取
    bookInfo: {},
    chapters: [],
    allChapters: [], // 保存所有章节数据，用于筛选
    filterOptions: [],
    currentFilter: 'all',
    currentFilterText: '全部章节',
    showFilterModal: false,
    loading: true,
  },

  onLoad(options) {
    // 获取状态栏高度
    const systemInfo = wx.getSystemInfoSync();
    this.setData({
      statusBarHeight: systemInfo.statusBarHeight || 44
    });

    // 获取传入的书籍ID（如果有）
    const bookId = options.bookId || '1';

    // 加载书籍详情数据
    this.loadBookDetail(bookId);
  },

  // 加载书籍详情数据
  async loadBookDetail(bookId) {
    try {
      this.setData({ loading: true });

      // 显示加载中
      wx.showLoading({
        title: '加载中...'
      });

      // 调用云函数获取数据
      const result = await wx.cloud.callFunction({
        name: 'bookDetailData',
        data: { bookId }
      });

      wx.hideLoading();

      if (result.result.code === 0) {
        const { bookInfo, chapters, filterOptions } = result.result.data;

        // 转换时长格式：秒 -> 小时+分钟
        const convertedBookInfo = this.convertDurationFormat(bookInfo);
        const convertedChapters = chapters.map(chapter => this.convertDurationFormat(chapter));

        this.setData({
          bookInfo: convertedBookInfo,
          chapters: convertedChapters,
          allChapters: convertedChapters, // 保存所有章节数据
          filterOptions,
          loading: false
        });
      } else {
        // 处理错误
        wx.showToast({
          title: result.result.message || '获取数据失败',
          icon: 'none',
          duration: 2000
        });
        this.setData({ loading: false });
      }

    } catch (error) {
      wx.hideLoading();
      console.error('加载书籍详情失败:', error);
      wx.showToast({
        title: '网络异常，请重试',
        icon: 'none',
        duration: 2000
      });
      this.setData({ loading: false });
    }
  },

  // 章节点击
  onChapterTap(e) {
    const chapter = e.currentTarget.dataset.chapter;

    if (chapter.status === 'locked') {
      wx.showToast({
        title: '需要激活会员解锁章节',
        icon: 'none',
        duration: 1500
      });
      return;
    }

    // 跳转到learning页面
    wx.navigateTo({
      url: `/pages/article-detail/index?chapterId=${chapter._id}&bookId=${this.data.bookInfo._id}&chapterTitle=${encodeURIComponent(chapter.title)}`
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

    let filteredChapters = this.data.allChapters;
    if (filterValue !== 'all') {
      filteredChapters = this.data.allChapters.filter(chapter => chapter.status === filterValue);
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
    // 刷新书籍数据以获取最新进度
    if (this.data.bookInfo._id) {
      this.loadBookDetail(this.data.bookInfo._id);
    }
  },

  // 下拉刷新
  async onPullDownRefresh() {
    try {
      // 重新加载数据
      await this.loadBookDetail(this.data.bookInfo._id || '1');
      wx.stopPullDownRefresh();
    } catch (error) {
      wx.stopPullDownRefresh();
    }
  },

  // 转换时长格式：秒 -> 小时+分钟
  convertDurationFormat(item) {
    const converted = { ...item };

    // 转换书籍总时长
    if (converted.total_duration) {
      converted.total_duration = this.formatDuration(converted.total_duration);
    }

    // 转换章节时长
    if (converted.duration) {
      converted.duration = this.formatDuration(converted.duration);
    }

    return converted;
  },

  // 格式化时长显示
  formatDuration(seconds) {
    if (!seconds || seconds <= 0) return '0分钟';

    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (hours > 0) {
      return `${hours}小时${minutes > 0 ? minutes + '分钟' : ''}`;
    } else {
      return `${minutes}分钟`;
    }
  },

  // 页面分享
  onShareAppMessage() {
    return {
      title: `《${this.data.bookInfo.title}》- 一起来学习英语吧`,
      path: `/pages/book-detail/index?bookId=${this.data.bookInfo._id}`,
      imageUrl: this.data.bookInfo.cover_url
    };
  },

  // 分享到朋友圈
  onShareTimeline() {
    return {
      title: `正在学习《${this.data.bookInfo.title}》`,
      imageUrl: this.data.bookInfo.cover_url
    };
  }
});