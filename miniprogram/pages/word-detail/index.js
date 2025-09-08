// 单词详情页面逻辑
Page({
  data: {
    // 当前选中的日期
    selectedDate: '',
    
    // tab相关
    activeTab: 'learned', // learned | reviewed
    
    // 单词列表
    words: [],
    loading: false,
  },

  onLoad(options) {
    wx.setNavigationBarTitle({
      title: '单词详情'
    });
    
    if (options.date) {
      // 从word-study页面跳转过来，显示该日期的单词列表
      this.setData({
        selectedDate: options.date
      });
      this.loadWordsByDate(options.date);
      
      // 设置页面标题显示日期
      const dateStr = this.formatDisplayDate(options.date);
      wx.setNavigationBarTitle({
        title: dateStr + ' 单词记录'
      });
    }
  },

  // 格式化显示日期
  formatDisplayDate(dateString) {
    const date = new Date(dateString);
    const month = date.getMonth() + 1;
    const day = date.getDate();
    return `${month}月${day}日`;
  },

  // 切换tab
  onTabChange(e) {
    const { tab } = e.currentTarget.dataset;
    this.setData({
      activeTab: tab
    });
    
    // 重新加载单词数据
    if (this.data.selectedDate) {
      this.loadWordsByDate(this.data.selectedDate);
    }
  },

  // 根据日期加载单词数据
  async loadWordsByDate(date) {
    try {
      this.setData({ loading: true });
      
      // 调用云函数获取指定日期的单词记录
      const result = await wx.cloud.callFunction({
        name: 'wordStudy',
        data: {
          action: 'getWordsByDate',
          date: date,
          type: this.data.activeTab
        }
      });

      if (result.result.success) {
        console.log("获取日期单词成功:", result.result.data);
        
        this.setData({
          words: result.result.data,
          loading: false
        });
      } else {
        console.error('获取日期单词失败:', result.result.message);
        wx.showToast({
          title: '加载失败',
          icon: 'none'
        });
        this.setData({ loading: false });
      }
    } catch (error) {
      console.error('加载日期单词错误:', error);
      wx.showToast({
        title: '加载失败',
        icon: 'none'
      });
      this.setData({ loading: false });
    }
  },

  // 单词点击事件（从word-list组件传递过来）
  onWordTap(e) {
    const { word, index } = e.detail;
    console.log('📚 [DEBUG] 点击单词:', word, '索引:', index);
    // 在单词详情页面中单词是只读的，不需要特殊处理
  }
});