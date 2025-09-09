// 单词本入口页面逻辑
Page({
  data: {
    // 各类单词数量
    newWordsCount: 0,
    reviewWordsCount: 0,
    overdueWordsCount: 0,

    // 页面状态
    loading: true,
    refreshing: false,

    // 日历相关
    monthInfo: {
      weekDays: ['日', '一', '二', '三', '四', '五', '六'],
      calendarDays: []
    }
  },

  onLoad(options) {
    wx.setNavigationBarTitle({
      title: '单词学习'
    });
    this.loadStudyStats();
    this.initCalendar(); // 初始化日历
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

  // 进入学习日历页面
  onEnterCalendar() {
    wx.navigateTo({
      url: '/pages/word-detail/index'
    });
  },

  // 下拉刷新处理
  async onRefresh() {
    console.log('🔄 [DEBUG] word-study页面用户触发下拉刷新');
    this.setData({ refreshing: true });

    try {
      // 重新加载学习统计数据
      await this.loadStudyStats();

      wx.showToast({
        title: '刷新成功',
        icon: 'success',
        duration: 1500
      });
    } catch (error) {
      console.error('❌ [DEBUG] word-study下拉刷新失败:', error);
      wx.showToast({
        title: '刷新失败',
        icon: 'none',
        duration: 2000
      });
    } finally {
      // 停止刷新状态
      this.setData({ refreshing: false });
    }
  },

  // 初始化日历
  initCalendar() {
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth() + 1;

    this.generateCalendar(year, month);
  },

  // 生成日历数据
  async generateCalendar(year, month) {
    const today = new Date();
    const todayStr = this.formatDate(today);

    // 获取当月第一天和最后一天
    const firstDay = new Date(year, month - 1, 1);
    const lastDay = new Date(year, month, 0);
    const daysInMonth = lastDay.getDate();

    // 获取当月第一天是星期几
    const firstDayWeek = firstDay.getDay();

    const calendarDays = [];

    // 添加当月日期
    for (let i = 1; i <= daysInMonth; i++) {
      const date = new Date(year, month - 1, i);
      const dateStr = this.formatDate(date);

      calendarDays.push({
        date: i,
        fullDate: dateStr,
        isToday: dateStr === todayStr,
        hasStudy: false,
        intensityLevel: 0
      });
    }

    // 加载学习统计数据
    console.log('📅 [DEBUG] 生成的初始日历数据:', calendarDays);
    await this.loadCalendarStats(year, month, calendarDays);

    console.log('📅 [DEBUG] loadCalendarStats执行后的日历数据:', calendarDays);
    // 移除重复的setData，因为loadCalendarStats内部已经正确设置了数据
    console.log('💾 [DEBUG] generateCalendar完成，当前页面数据:', this.data.monthInfo.calendarDays);
  },

  // 格式化日期为YYYY-MM-DD
  formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  },

  // 加载日历统计数据
  async loadCalendarStats(year, month, calendarDays) {
    try {
      // 如果没有传入参数，使用当前数据
      if (!year || !month || !calendarDays) {
        year = this.data.currentYear;
        month = this.data.currentMonth;
        calendarDays = this.data.monthInfo?.calendarDays || [];
      }

      // 获取当前月份的第一天和最后一天
      const firstDay = new Date(year, month - 1, 1);
      const lastDay = new Date(year, month, 0);

      const startDate = this.formatDate(firstDay);
      const endDate = this.formatDate(lastDay);

      // 调用云函数获取日期统计数据
      console.log('☁️ [DEBUG] 准备调用云函数 getDailyStats，参数:', { startDate, endDate });
      const { result } = await wx.cloud.callFunction({
        name: 'wordStudy',
        data: {
          action: 'getDailyStats',
          params: {
            startDate,
            endDate
          }
        }
      });

      console.log('☁️ [DEBUG] 云函数 getDailyStats 返回结果:', result);

      if (result.success && result.data) {
        // 创建日期到强度等级的映射
        const dateToIntensityMap = {};
        console.log('📊 [DEBUG] 开始处理云函数返回的统计数据，数量:', result.data.length);

        result.data.forEach(item => {
          const learnedCount = item.learned_count || 0;
          const reviewedCount = item.reviewed_count || 0;
          const intensityLevel = this.calculateIntensityLevel(learnedCount, reviewedCount);
          dateToIntensityMap[item.date] = intensityLevel;
          console.log(`📊 [DEBUG] 日期 ${item.date}: learned=${learnedCount}, reviewed=${reviewedCount}, intensity=${intensityLevel}`);
        });

        console.log('📊 [DEBUG] 构建完成的强度映射表:', dateToIntensityMap);

        // 更新日历天数的强度等级
        if (calendarDays && calendarDays.length > 0) {
          console.log('🔄 [DEBUG] 开始更新日历数据，原始calendarDays数量:', calendarDays.length);
          const updatedDays = calendarDays.map(day => {
            if (day.fullDate && dateToIntensityMap[day.fullDate]) {
              const updatedDay = { ...day, intensityLevel: dateToIntensityMap[day.fullDate], hasStudy: true };
              console.log(`🔄 [DEBUG] 更新日期 ${day.fullDate}: intensity=${dateToIntensityMap[day.fullDate]}`);
              return updatedDay;
            }
            return day;
          });

          console.log('🔄 [DEBUG] 更新完成的日历数据:', updatedDays);
          this.setData({
            'monthInfo.calendarDays': updatedDays
          });
          console.log('💾 [DEBUG] setData后的页面数据:', this.data.monthInfo.calendarDays);
        }
      }
    } catch (error) {
      console.error('加载日历统计失败:', error);
    }
  },

  // 计算学习强度等级（0-4）
  calculateIntensityLevel(learnedCount, reviewedCount) {
    // 计算学习强度 (基数20)
    let learnIntensity;
    if (learnedCount === 0) learnIntensity = 0;
    else if (learnedCount <= 5) learnIntensity = 1;   // 1-5个
    else if (learnedCount <= 10) learnIntensity = 2;  // 6-10个
    else if (learnedCount <= 15) learnIntensity = 3;  // 11-15个
    else learnIntensity = 4;                          // 16+个

    // 计算复习强度 (基数120)
    let reviewIntensity;
    if (reviewedCount === 0) reviewIntensity = 0;
    else if (reviewedCount <= 30) reviewIntensity = 1;   // 1-30个
    else if (reviewedCount <= 60) reviewIntensity = 2;   // 31-60个
    else if (reviewedCount <= 90) reviewIntensity = 3;   // 61-90个
    else reviewIntensity = 4;                            // 91+个

    // 取最大值
    const intensityLevel = Math.max(learnIntensity, reviewIntensity);
    
    console.log(`🎯 [DEBUG] calculateIntensityLevel: learned=${learnedCount}(${learnIntensity}), reviewed=${reviewedCount}(${reviewIntensity}) -> intensity=${intensityLevel}`);
    return intensityLevel;
  },

  // 日历日期点击事件
  onCalendarDayTap(e) {
    const { fullDate } = e.currentTarget.dataset;

    // 确保有完整日期才进行跳转，并检查fullDate是否为有效字符串
    if (fullDate && typeof fullDate === 'string' && fullDate.length > 0) {
      wx.navigateTo({
        url: `/pages/word-detail/index?date=${fullDate}`
      });
    } else {
      console.warn('无效的日期数据，无法跳转:', fullDate);
    }
  },

});