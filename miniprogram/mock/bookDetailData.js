// book-detail页面mock数据
const bookDetailData = {
  // 书籍基本信息
  bookInfo: {
    id: 1,
    title: '哈利·波特与魔法石',
    author: 'J.K. 罗琳',
    cover: 'https://images.unsplash.com/photo-1589829085413-56de8ae18c73?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80',
    stats: {
      chapters: '17章',
      duration: '8小时',
      vocabulary: '523单词'
    },
    progress: 35, // 已完成百分比
    description: '《哈利·波特与魔法石》是J.K.罗琳创作的魔幻文学系列的第一部。故事讲述了年幼的哈利·波特在父母被杀害后，被送到姨父姨妈家寄养。在十一岁生日那天，哈利得知自己是一名巫师，并被霍格沃茨魔法学校录取。在学校里，哈利结交了朋友，发现了自己的天赋，并揭开了魔法石的秘密。',
    tags: ['奇幻', '冒险', '青少年'],
    isFavorited: false
  },

  // 章节列表
  chapters: [
    {
      id: 1,
      title: '第1章 - 大难不死的男孩',
      vocabulary: 42,
      duration: '18分钟',
      status: 'completed', // completed, in-progress, available, locked
      progress: 100
    },
    {
      id: 2,
      title: '第2章 - 消失的玻璃',
      vocabulary: 38,
      duration: '22分钟',
      status: 'completed',
      progress: 100
    },
    {
      id: 3,
      title: '第3章 - 猫头鹰传书',
      vocabulary: 45,
      duration: '25分钟',
      status: 'in-progress',
      progress: 75
    },
    {
      id: 4,
      title: '第4章 - 钥匙保管员',
      vocabulary: 51,
      duration: '28分钟',
      status: 'available',
      progress: 0
    },
    {
      id: 5,
      title: '第5章 - 对角巷',
      vocabulary: 47,
      duration: '24分钟',
      status: 'available',
      progress: 0
    },
    {
      id: 6,
      title: '第6章 - 从9¾站台出发',
      vocabulary: 39,
      duration: '20分钟',
      status: 'locked',
      progress: 0
    },
    {
      id: 7,
      title: '第7章 - 分院帽',
      vocabulary: 44,
      duration: '26分钟',
      status: 'locked',
      progress: 0
    },
    {
      id: 8,
      title: '第8章 - 魔药课老师',
      vocabulary: 48,
      duration: '23分钟',
      status: 'locked',
      progress: 0
    },
    {
      id: 9,
      title: '第9章 - 午夜决斗',
      vocabulary: 41,
      duration: '21分钟',
      status: 'locked',
      progress: 0
    },
    {
      id: 10,
      title: '第10章 - 万圣节',
      vocabulary: 46,
      duration: '27分钟',
      status: 'locked',
      progress: 0
    },
    {
      id: 11,
      title: '第11章 - 魁地奇比赛',
      vocabulary: 52,
      duration: '30分钟',
      status: 'locked',
      progress: 0
    },
    {
      id: 12,
      title: '第12章 - 厄里斯魔镜',
      vocabulary: 43,
      duration: '25分钟',
      status: 'locked',
      progress: 0
    },
    {
      id: 13,
      title: '第13章 - 尼可·勒梅',
      vocabulary: 40,
      duration: '22分钟',
      status: 'locked',
      progress: 0
    },
    {
      id: 14,
      title: '第14章 - 挪威脊背龙',
      vocabulary: 38,
      duration: '19分钟',
      status: 'locked',
      progress: 0
    },
    {
      id: 15,
      title: '第15章 - 禁林',
      vocabulary: 45,
      duration: '24分钟',
      status: 'locked',
      progress: 0
    },
    {
      id: 16,
      title: '第16章 - 穿越活板门',
      vocabulary: 49,
      duration: '28분钟',
      status: 'locked',
      progress: 0
    },
    {
      id: 17,
      title: '第17章 - 双面人',
      vocabulary: 42,
      duration: '26분钟',
      status: 'locked',
      progress: 0
    }
  ],

  // 章节过滤选项
  filterOptions: [
    { value: 'all', label: '全部章节' },
    { value: 'completed', label: '已学习' },
    { value: 'available', label: '可学习' },
    { value: 'locked', label: '未解锁' }
  ]
};

module.exports = bookDetailData;