// home页面mock数据
const homeData = {
  // 最近学习的书籍
  recentBooks: [
    {
      id: 1,
      title: '哈利·波特与魔法石',
      author: 'J.K. 罗琳',
      cover: 'https://images.unsplash.com/photo-1481627834876-b7833e8f5570?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80',
      progress: 35
    },
    {
      id: 2,
      title: '小王子',
      author: '安托万·德·圣埃克苏佩里',
      cover: 'https://images.unsplash.com/photo-1544947950-fa07a98d237f?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80',
      progress: 15
    },
    {
      id: 3,
      title: '了不起的盖茨比',
      author: 'F.司各特·菲茨杰拉德',
      cover: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80',
      progress: 68
    },
    {
      id: 4,
      title: '牛奶与蜂蜜',
      author: 'rupi kaur',
      cover: 'https://images.unsplash.com/photo-1589829085413-56de8ae18c73?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80',
      progress: 22
    }
  ],

  // 分类标签
  categories: [
    { id: 'literature', name: '文学名著', active: true },
    { id: 'business', name: '商业英语', active: false },
    { id: 'script', name: '影视剧本', active: false },
    { id: 'news', name: '新闻', active: false }
  ],

  // 分类书籍数据
  categoryBooks: {
    literature: [
      {
        id: 1,
        title: '了不起的盖茨比',
        author: 'F.司各特·菲茨杰拉德',
        cover: 'https://images.unsplash.com/photo-1621351183012-e2f9972dd9bf?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80'
      },
      {
        id: 2,
        title: '双塔奇兵',
        author: 'J.R.R. 托尔金',
        cover: 'https://img9.doubanio.com/view/photo/s_ratio_poster/public/p2640236255.webp'
      },
      {
        id: 3,
        title: '动物农场',
        author: '乔治·奥威尔',
        cover: 'https://images.unsplash.com/photo-1544716278-ca5e3f4abd8c?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80'
      },
      {
        id: 4,
        title: '海边的卡夫卡',
        author: '村上春树',
        cover: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80'
      }
    ],
    business: [
      {
        id: 5,
        title: '商务英语口语精选',
        author: '李明',
        cover: 'https://images.unsplash.com/photo-1560472354-b33ff0c44a43?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80'
      },
      {
        id: 6,
        title: '职场沟通技巧',
        author: '张华',
        cover: 'https://images.unsplash.com/photo-1553028826-f4804a6dba3b?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80'
      },
      {
        id: 7,
        title: '国际贸易英语',
        author: '王磊',
        cover: 'https://images.unsplash.com/photo-1554415707-6e8cfc93fe23?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80'
      },
      {
        id: 8,
        title: '会议英语实用手册',
        author: '刘芳',
        cover: 'https://images.unsplash.com/photo-1552664730-d307ca884978?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80'
      }
    ],
    script: [
      {
        id: 9,
        title: '老友记经典台词',
        author: 'NBC',
        cover: 'https://img1.doubanio.com/view/photo/l/public/p2607581180.webp'
      },
      {
        id: 10,
        title: '权力的游戏剧本',
        author: 'HBO',
        cover: 'https://images.unsplash.com/photo-1518929458119-e5bf444c30f4?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80'
      },
      {
        id: 11,
        title: '神探夏洛克对白',
        author: 'BBC',
        cover: 'https://images.unsplash.com/photo-1481627834876-b7833e8f5570?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80'
      },
      {
        id: 12,
        title: '复仇者联盟台词集',
        author: 'Marvel',
        cover: 'https://images.unsplash.com/photo-1598300042247-d088f8ab3a91?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80'
      }
    ],
    news: [
      {
        id: 13,
        title: 'BBC新闻精选',
        author: 'BBC',
        cover: 'https://images.unsplash.com/photo-1586953208448-b95a79798f07?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80'
      },
      {
        id: 14,
        title: 'CNN时事英语',
        author: 'CNN',
        cover: 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80'
      },
      {
        id: 15,
        title: '经济学人精读',
        author: 'The Economist',
        cover: 'https://images.unsplash.com/photo-1612178537253-bccd437b730e?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80'
      },
      {
        id: 16,
        title: '国际时政要闻',
        author: 'Reuters',
        cover: 'https://images.unsplash.com/photo-1495020689067-958852a7765e?ixlib=rb-4.0.3&auto=format&fit=crop&w=400&q=80'
      }
    ]
  }
};

module.exports = homeData;