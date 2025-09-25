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
    // 分页相关
    currentPage: 1,
    pageSize: 20,
    hasMoreChapters: true,
    loadingMore: false,
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
  async loadBookDetail(bookId, isFirstLoad = true) {
    try {
      if (isFirstLoad) {
        this.setData({ loading: true });
        wx.showLoading({ title: '加载中...' });
      } else {
        this.setData({ loadingMore: true });
      }

      const { currentPage, pageSize } = this.data;
      const requestPage = isFirstLoad ? 1 : currentPage;

      // 调用云函数获取数据
      const result = await wx.cloud.callFunction({
        name: 'bookDetailData',
        data: {
          bookId,
          page: requestPage,
          pageSize: pageSize
        }
      });

      if (isFirstLoad) {
        wx.hideLoading();
      }

      if (result.result.code === 0) {
        const { bookInfo, chapters, filterOptions, hasMoreChapters } = result.result.data;

        // 转换时长格式：秒 -> 小时+分钟
        const convertedBookInfo = this.convertDurationFormat(bookInfo);
        const convertedChapters = chapters.map(chapter => this.convertDurationFormat(chapter));

        if (isFirstLoad) {
          // 首次加载
          this.setData({
            bookInfo: convertedBookInfo,
            chapters: convertedChapters,
            allChapters: convertedChapters,
            filterOptions,
            hasMoreChapters,
            currentPage: 1,
            loading: false
          });
        } else {
          // 分页加载
          const existingChapters = this.data.chapters;
          const allChapters = [...this.data.allChapters, ...convertedChapters];

          this.setData({
            chapters: [...existingChapters, ...convertedChapters],
            allChapters: allChapters,
            hasMoreChapters,
            currentPage: requestPage,
            loadingMore: false
          });
        }
      } else {
        // 处理错误
        wx.showToast({
          title: result.result.message || '获取数据失败',
          icon: 'none',
          duration: 2000
        });
        this.setData({
          loading: isFirstLoad ? false : this.data.loading,
          loadingMore: false
        });
      }

    } catch (error) {
      if (isFirstLoad) {
        wx.hideLoading();
      }
      console.error('加载书籍详情失败:', error);
      wx.showToast({
        title: '网络异常，请重试',
        icon: 'none',
        duration: 2000
      });
      this.setData({
        loading: isFirstLoad ? false : this.data.loading,
        loadingMore: false
      });
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

  // 滚动到底部加载更多章节
  async onScrollToLower() {
    const { hasMoreChapters, loadingMore, bookInfo } = this.data;

    // 如果没有更多数据或正在加载中，则返回
    if (!hasMoreChapters || loadingMore) {
      return;
    }

    console.log('📄 [DEBUG] 滚动到底部，加载更多章节');
    const nextPage = this.data.currentPage + 1;
    this.setData({ currentPage: nextPage });

    await this.loadBookDetail(bookInfo._id, false);
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
      converted.total_duration = this.formatDurationMinutes(converted.total_duration);
    }

    // 转换章节时长
    if (converted.duration) {
      converted.duration = this.formatDurationSeconds(converted.duration);
    }

    return converted;
  },

  // 格式化时长显示
  formatDurationMinutes(_seconds) {
    if (!_seconds || _seconds <= 0) return '0分钟';

    const hours = Math.floor(_seconds / 3600);
    const minutes = Math.floor((_seconds % 3600) / 60);
    return `${hours}小时${minutes}分钟`
  },

  formatDurationSeconds(_seconds) {
    if (!_seconds || _seconds <= 0) return '0秒';

    const minutes = Math.floor(_seconds / 60);
    const seconds = Math.floor(_seconds % 60);
    return `${minutes}分钟${seconds}秒`
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