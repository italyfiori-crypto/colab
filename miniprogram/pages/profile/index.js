// profile页面逻辑
const profileData = require('../../mock/profileData.js');

Page({
  data: {
    userInfo: {},
    studyStats: [],
    monthInfo: {},
    studyCalendar: {}
  },

  onLoad() {
    this.loadProfileData();
  },

  // 加载用户资料数据
  loadProfileData() {
    const { userInfo, studyStats, monthInfo, studyCalendar } = profileData;
    
    this.setData({
      userInfo: userInfo,
      studyStats: studyStats,
      monthInfo: monthInfo,
      studyCalendar: studyCalendar
    });
  },

  // 页面显示时触发
  onShow() {
    // 每次显示页面时刷新数据
    this.loadProfileData();
  },

  // 下拉刷新
  onPullDownRefresh() {
    // 重新加载数据
    this.loadProfileData();
    
    // 延迟关闭下拉刷新
    setTimeout(() => {
      wx.stopPullDownRefresh();
    }, 1000);
  },

  // 页面分享
  onShareAppMessage() {
    return {
      title: '我的学习成果 - 英语学习',
      path: '/pages/profile/index'
    };
  },

  // 分享到朋友圈
  onShareTimeline() {
    return {
      title: '我的学习成果 - 英语学习'
    };
  }
});