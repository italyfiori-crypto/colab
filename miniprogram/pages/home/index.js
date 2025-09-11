// home页面逻辑
Page({
  data: {
    searchKeyword: '',
    recentBooks: [],
    categories: [],
    currentCategoryBooks: [],
    currentCategory: '文学名著',
    currentTab: 'home',
    // 搜索结果相关
    searchResults: [],
    showSearchResults: false,
    searchLoading: false
  },

  onLoad() {
    this.loadData();
  },

  // 加载页面数据
  async loadData() {
    try {
      console.log('🔄 [DEBUG] 开始加载首页数据, 当前分类:', this.data.currentCategory)
      wx.showLoading({ title: '加载中...' })

      const requestData = {
        type: 'getHomeData',
        category: this.data.currentCategory
      }
      console.log('📤 [DEBUG] 发送请求数据:', requestData)

      const result = await wx.cloud.callFunction({
        name: 'homeData',
        data: requestData
      })

      console.log('📥 [DEBUG] 收到响应:', result)

      if (result.result.code === 0) {
        const { recentBooks, categoryBooks, categories } = result.result.data
        console.log('✅ [DEBUG] 数据解析成功:')
        console.log('  - 最近阅读:', recentBooks?.length || 0, '本')
        console.log('  - 分类书籍:', categoryBooks?.length || 0, '本')
        console.log('  - 分类列表:', categories?.length || 0, '个')

        this.setData({
          recentBooks: recentBooks,
          currentCategoryBooks: categoryBooks,
          categories: categories
        })
        console.log('💾 [DEBUG] 数据已更新到页面状态')
      } else {
        console.error('❌ [DEBUG] 服务端返回错误:', result.result)
        wx.showToast({
          title: '加载失败: ' + result.result.message,
          icon: 'error'
        })
      }
    } catch (err) {
      console.error('❌ [DEBUG] 加载首页数据失败:', err)
      wx.showToast({
        title: '网络错误',
        icon: 'error'
      })
    } finally {
      wx.hideLoading()
    }
  },

  // 单独加载最近阅读
  async loadRecentBooks() {
    try {
      console.log('🔄 [DEBUG] 开始加载最近阅读数据')
      const requestData = { type: 'getRecentBooks' }
      console.log('📤 [DEBUG] 发送请求数据:', requestData)

      const result = await wx.cloud.callFunction({
        name: 'homeData',
        data: requestData
      })

      console.log('📥 [DEBUG] 最近阅读响应:', result)

      if (result.result.code === 0) {
        console.log('✅ [DEBUG] 最近阅读数据:', result.result.data?.length || 0, '本')
        this.setData({
          recentBooks: result.result.data
        })
        console.log('💾 [DEBUG] 最近阅读数据已更新到页面状态')
      } else {
        console.error('❌ [DEBUG] 最近阅读服务端返回错误:', result.result)
      }
    } catch (err) {
      console.error('❌ [DEBUG] 加载最近阅读失败:', err)
    }
  },

  // 搜索输入处理
  onSearchInput(e) {
    const keyword = e.detail.value;
    this.setData({
      searchKeyword: keyword
    });

    // 如果搜索框被清空，恢复正常状态
    if (!keyword.trim()) {
      this.setData({
        showSearchResults: false,
        searchResults: []
      });
    }
  },

  // 搜索确认处理
  async onSearchConfirm(e) {
    const keyword = e.detail.value.trim();
    if (keyword) {
      try {
        console.log('🔍 [DEBUG] 开始搜索, 关键词:', keyword)

        this.setData({
          searchLoading: true
        })
        wx.showLoading({ title: '搜索中...' })

        const requestData = {
          type: 'searchBooks',
          keyword: keyword
        }
        console.log('📤 [DEBUG] 发送搜索请求:', requestData)

        const result = await wx.cloud.callFunction({
          name: 'homeData',
          data: requestData
        })

        console.log('📥 [DEBUG] 搜索响应:', result)

        if (result.result.code === 0) {
          console.log('✅ [DEBUG] 搜索结果:', result.result.data?.length || 0, '本')

          // 保存搜索结果并显示搜索结果区域
          this.setData({
            searchResults: result.result.data,
            showSearchResults: true,
            searchLoading: false
          })
        } else {
          console.error('❌ [DEBUG] 搜索服务端返回错误:', result.result)
          this.setData({
            searchLoading: false
          })
        }
      } catch (err) {
        console.error('❌ [DEBUG] 搜索失败:', err)
        this.setData({
          searchLoading: false
        })
        wx.showToast({
          title: '搜索失败',
          icon: 'error'
        })
      } finally {
        wx.hideLoading()
      }
    } else {
      // 搜索关键词为空，恢复正常状态
      console.log('⚠️ [DEBUG] 搜索关键词为空，恢复正常状态')
      this.setData({
        showSearchResults: false,
        searchResults: []
      })
    }
  },

  // 分类标签点击处理
  async onCategoryTap(e) {
    const categoryName = e.currentTarget.dataset.category;
    console.log('🏷️ [DEBUG] 点击分类标签:', categoryName)

    // 更新分类状态
    const categories = this.data.categories.map(cat => ({
      ...cat,
      active: cat.name === categoryName
    }));

    this.setData({
      categories: categories,
      currentCategory: categoryName
    });
    console.log('💾 [DEBUG] 分类状态已更新')

    try {
      wx.showLoading({ title: '加载中...' })

      const requestData = {
        type: 'getCategoryBooks',
        category: categoryName
      }
      console.log('📤 [DEBUG] 发送分类请求:', requestData)

      const result = await wx.cloud.callFunction({
        name: 'homeData',
        data: requestData
      })

      console.log('📥 [DEBUG] 分类响应:', result)
      wx.hideLoading()

      if (result.result.code === 0) {
        console.log('✅ [DEBUG] 分类书籍数据:', result.result.data?.length || 0, '本')
        this.setData({
          currentCategoryBooks: result.result.data
        })
        console.log('💾 [DEBUG] 分类书籍数据已更新到页面状态')
      } else {
        console.error('❌ [DEBUG] 分类服务端返回错误:', result.result)
      }
    } catch (err) {
      wx.hideLoading()
      console.error('❌ [DEBUG] 切换分类失败:', err)
      wx.showToast({
        title: '加载失败',
        icon: 'error'
      })
    }
  },

  // 书籍点击处理 - 添加到最近阅读
  async onBookTap(e) {
    const bookId = e.currentTarget.dataset.bookId;
    const book = e.currentTarget.dataset.book;

    console.log('📖 [DEBUG] 点击书籍:', bookId, book?.title || '未知书籍');

    try {
      // 1. 添加到最近阅读列表
      console.log('🔄 [DEBUG] 开始添加到最近阅读')
      wx.showLoading({ title: '加载中...' });

      const requestData = {
        type: 'addToRecent',
        book_id: bookId
      }
      console.log('📤 [DEBUG] 发送添加到最近阅读请求:', requestData)

      const result = await wx.cloud.callFunction({
        name: 'homeData',
        data: requestData
      });

      console.log('📥 [DEBUG] 添加到最近阅读响应:', result)
      wx.hideLoading();

      if (result.result.code === 0) {
        console.log('✅ [DEBUG] 成功添加到最近阅读')
        // 2. 刷新最近阅读列表
        this.loadRecentBooks();
      } else {
        console.error('❌ [DEBUG] 添加到最近阅读失败:', result.result)
      }

      // 3. 跳转到书籍详情页
      console.log('🔄 [DEBUG] 跳转到书籍详情页:', bookId)
      wx.navigateTo({
        url: `/pages/book-detail/index?bookId=${bookId}`
      });

    } catch (err) {
      wx.hideLoading();
      console.error('❌ [DEBUG] 处理书籍点击失败:', err);

      // 即使添加到最近阅读失败，也要跳转到详情页
      console.log('🔄 [DEBUG] 异常情况下跳转到书籍详情页:', bookId)
      wx.navigateTo({
        url: `/pages/book-detail/index?bookId=${bookId}`
      });
    }
  },

  // 书籍封面加载错误处理
  onBookCoverError(e) {
    const index = e.currentTarget.dataset.index;
    const currentUrl = e.currentTarget.dataset.src;
    
    console.error('❌ [DEBUG] 书籍封面加载失败:', { index, currentUrl });
    
    // 获取设置工具
    const settingsUtils = require('../../utils/settingsUtils.js');
    
    // 尝试使用代理服务
    if (currentUrl && !currentUrl.includes('images.weserv.nl')) {
      const proxyUrl = settingsUtils.getProxyImageUrl(currentUrl);
      console.log('🔄 [DEBUG] 使用代理URL加载封面:', proxyUrl);
      
      // 更新对应的书籍封面URL
      if (this.data.showSearchResults) {
        this.setData({
          [`searchResults[${index}].cover_url`]: proxyUrl
        });
      } else {
        // 需要判断是哪个列表中的书籍
        if (index < this.data.featuredBooks.length) {
          this.setData({
            [`featuredBooks[${index}].cover_url`]: proxyUrl
          });
        } else {
          const popularIndex = index - this.data.featuredBooks.length;
          this.setData({
            [`popularBooks[${popularIndex}].cover_url`]: proxyUrl
          });
        }
      }
    } else {
      console.log('⚠️ [DEBUG] 封面加载最终失败，使用默认封面');
      // 可以设置默认封面或隐藏图片
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
    console.log('🔄 [DEBUG] 页面显示, 设置当前标签为首页')
    // 确保当前标签页为首页
    this.setData({
      currentTab: 'home'
    });
  },

  // 下拉刷新
  onPullDownRefresh() {
    console.log('🔄 [DEBUG] 触发下拉刷新')
    // 重新加载数据
    this.loadData().then(() => {
      console.log('✅ [DEBUG] 下拉刷新数据加载成功')
      wx.stopPullDownRefresh();
    }).catch((err) => {
      console.error('❌ [DEBUG] 下拉刷新数据加载失败:', err)
      wx.stopPullDownRefresh();
    });
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