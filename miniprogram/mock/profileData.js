// profile页面模拟数据
const profileData = {
  // 用户基本信息
  userInfo: {
    name: 'Sarah Johnson',
    avatar: '/resource/icons/avatar.svg', // 头像占位
    studyDays: 12, // 连续学习天数
    totalStudyTime: 24.5, // 总学习时长(小时)
    chaptersCompleted: 32, // 已读章节
    vocabularyMastered: 76 // 掌握单词数
  },

  // 学习日历数据
  studyCalendar: {
    currentMonth: '2024年12月', // 当前月份
    studyDates: [
      2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 // 有学习记录的日期
    ],
    todayDate: 12 // 今天是几号
  },

  // 学习统计数据
  studyStats: [
    {
      id: 1,
      iconPath: '/resource/icons/stat-calendar-check.svg',
      value: '12',
      label: '连续学习',
      unit: '天'
    },
    {
      id: 2,
      iconPath: '/resource/icons/stat-clock.svg',
      value: '24.5',
      label: '总学习时长',
      unit: '小时'
    },
    {
      id: 3,
      iconPath: '/resource/icons/stat-book.svg',
      value: '32',
      label: '已读章节',
      unit: '章'
    },
    {
      id: 4,
      iconPath: '/resource/icons/stat-graduation-cap.svg',
      value: '76',
      label: '掌握单词',
      unit: '个'
    }
  ],

  // 月份信息
  monthInfo: {
    weekDays: ['一', '二', '三', '四', '五', '六', '日'],
    // 生成12月份的日历数据 (2024年12月1日是周日)
    calendarDays: [
      // 第一周 (1号是周日，前面需要填空格)
      { date: null }, { date: null }, { date: null }, { date: null }, { date: null }, { date: null }, { date: 1 },
      // 第二周
      { date: 2, hasStudy: true }, { date: 3, hasStudy: true }, { date: 4, hasStudy: true }, { date: 5, hasStudy: true }, { date: 6, hasStudy: true }, { date: 7, hasStudy: true }, { date: 8, hasStudy: true },
      // 第三周
      { date: 9, hasStudy: true }, { date: 10, hasStudy: true }, { date: 11, hasStudy: true }, { date: 12, hasStudy: true, isToday: true }, { date: 13 }, { date: 14 }, { date: 15 },
      // 第四周
      { date: 16 }, { date: 17 }, { date: 18 }, { date: 19 }, { date: 20 }, { date: 21 }, { date: 22 },
      // 第五周
      { date: 23 }, { date: 24 }, { date: 25 }, { date: 26 }, { date: 27 }, { date: 28 }, { date: 29 },
      // 第六周
      { date: 30 }, { date: 31 }
    ]
  }
};

module.exports = profileData;