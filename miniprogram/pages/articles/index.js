Page({
    data: {
        searchValue: '',
        activeTab: 0,
        activeNavIndex: 0,
        tabs: ['全部', '日常对话', '商务英语', '旅游英语', '学术英语'],
        navItems: [
            {
                name: '首页',
                icon: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEwIDIwVjE0SDEyVjIwSDIxVjEySDI0TDEyIDFMMCAxMkgzVjIwSDEwWiIgZmlsbD0iIzk5OSIvPgo8L3N2Zz4K',
                activeIcon: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEwIDIwVjE0SDEyVjIwSDIxVjEySDI0TDEyIDFMMCAxMkgzVjIwSDEwWiIgZmlsbD0iIzQzODVGRiIvPgo8L3N2Zz4K'
            },
            {
                name: '学习记录',
                icon: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEyIDJMMTMuMDkgOC4yNkwyMCA5TDEzLjA5IDE1Ljc0TDEyIDIyTDEwLjkxIDE1Ljc0TDQgOUwxMC45MSA4LjI2TDEyIDJaIiBmaWxsPSIjOTk5Ii8+Cjwvc3ZnPgo=',
                activeIcon: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEyIDJMMTMuMDkgOC4yNkwyMCA5TDEzLjA5IDE1Ljc0TDEyIDIyTDEwLjkxIDE1Ljc0TDQgOUwxMC45MSA4LjI2TDEyIDJaIiBmaWxsPSIjNDM4NUZGIi8+Cjwvc3ZnPgo='
            },
            {
                name: '收藏',
                icon: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEyIDIxLjM1TDEwLjU1IDIwLjAzQzUuNCAxNS4zNiAyIDEyLjI4IDIgOC41QzIgNS40MiA0LjQyIDMgNy41IDNDOS4yNCAzIDEwLjkxIDMuODEgMTIgNS4wOUMxMy4wOSAzLjgxIDE0Ljc2IDMgMTYuNSAzQzE5LjU4IDMgMjIgNS40MiAyMiA4LjVDMjIgMTIuMjggMTguNiAxNS4zNiAxMy40NSAyMC4wNEwxMiAyMS4zNVoiIHN0cm9rZT0iIzk5OSIgc3Ryb2tlLXdpZHRoPSIyIiBmaWxsPSJub25lIi8+Cjwvc3ZnPgo=',
                activeIcon: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEyIDIxLjM1TDEwLjU1IDIwLjAzQzUuNCAxNS4zNiAyIDEyLjI4IDIgOC41QzIgNS40MiA0LjQyIDMgNy41IDNDOS4yNCAzIDEwLjkxIDMuODEgMTIgNS4wOUMxMy4wOSAzLjgxIDE0Ljc2IDMgMTYuNSAzQzE5LjU4IDMgMjIgNS40MiAyMiA4LjVDMjIgMTIuMjggMTguNiAxNS4zNiAxMy40NSAyMC4wNEwxMiAyMS4zNVoiIGZpbGw9IiM0Mzg1RkYiLz4KPC9zdmc+Cg=='
            },
            {
                name: '我的',
                icon: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEyIDEyQzE0LjIwOTEgMTIgMTYgMTAuMjA5MSAxNiA4QzE2IDUuNzkwODYgMTQuMjA5MSA0IDEyIDRDOS43OTA4NiA0IDggNS43OTA4NiA4IDhDOCAxMC4yMDkxIDkuNzkwODYgMTIgMTJaTTEyIDEzLjVDOS4wMTUgMTMuNSA0IDE0Ljk5IDQgMThWMjBIMjBWMThDMjAgMTQuOTkgMTQuOTg1IDEzLjUgMTIgMTMuNVoiIGZpbGw9IiM5OTkiLz4KPC9zdmc+Cg==',
                activeIcon: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEyIDEyQzE0LjIwOTEgMTIgMTYgMTAuMjA5MSAxNiA4QzE2IDUuNzkwODYgMTQuMjA5MSA0IDEyIDRDOS43OTA4NiA0IDggNS43OTA4NiA4IDhDOCAxMC4yMDkxIDkuNzkwODYgMTIgMTJaTTEyIDEzLjVDOS4wMTUgMTMuNSA0IDE0Ljk5IDQgMThWMjBIMjBWMThDMjAgMTQuOTkgMTQuOTg1IDEzLjUgMTIgMTMuNVoiIGZpbGw9IiM0Mzg1RkYiLz4KPC9zdmc+Cg=='
            }
        ],
        articles: [
            {
                id: 1,
                category: '日常对话',
                title: 'Coffee Shop Conversation',
                description: 'Learn natural English expressions used when ordering coffee and having casual conversations at a cafe.',
                duration: '5分钟',
                level: '初级',
                image: 'https://images.unsplash.com/photo-1501339847302-ac426a4a7cbb?w=400&h=250&fit=crop'
            },
            {
                id: 2,
                category: '商务英语',
                title: 'Business Meeting Essentials',
                description: 'Master professional English phrases and vocabulary for effective business meetings and presentations.',
                duration: '8分钟',
                level: '中级',
                image: 'https://images.unsplash.com/photo-1552664730-d307ca884978?w=400&h=250&fit=crop'
            },
            {
                id: 3,
                category: '旅游英语',
                title: 'Airport Check-in Guide',
                description: 'Essential English phrases for smooth airport check-in, security, and boarding procedures.',
                duration: '6分钟',
                level: '初级',
                image: 'https://plus.unsplash.com/premium_photo-1661501562127-a8bb26defb35?q=80&w=2670&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D'
            },
            {
                id: 4,
                category: '学术英语',
                title: 'Academic Presentation Skills',
                description: 'Develop advanced vocabulary and presentation techniques for academic and professional settings.',
                duration: '12分钟',
                level: '高级',
                image: 'https://images.unsplash.com/photo-1524178232363-1fb2b075b655?w=400&h=250&fit=crop'
            },
            {
                id: 5,
                category: '日常对话',
                title: 'Shopping Conversations',
                description: 'Practice common English phrases used while shopping, asking for prices, and making purchases.',
                duration: '7分钟',
                level: '初级',
                image: 'https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=400&h=250&fit=crop'
            },
            {
                id: 6,
                category: '商务英语',
                title: 'Email Writing Mastery',
                description: 'Learn to write professional emails with proper tone, structure, and business terminology.',
                duration: '10分钟',
                level: '中级',
                image: 'https://images.unsplash.com/photo-1557200134-90327ee9fafa?q=80&w=2670&auto=format&fit=crop&ixlib=rb-4.1.0&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D'
            }
        ],
        filteredArticles: []
    },

    onLoad() {
        this.filterArticles();
    },

    // 搜索输入
    onSearchInput(e) {
        this.setData({
            searchValue: e.detail.value
        });
        this.filterArticles();
    },

    // 标签切换
    onTabChange(e) {
        const index = e.currentTarget.dataset.index;
        this.setData({
            activeTab: index
        });
        this.filterArticles();
    },

    // 过滤文章
    filterArticles() {
        const { articles, activeTab, tabs, searchValue } = this.data;
        let filtered = articles;

        // 按分类过滤
        if (activeTab > 0) {
            const category = tabs[activeTab];
            filtered = filtered.filter(article => article.category === category);
        }

        // 按搜索关键词过滤
        if (searchValue.trim()) {
            filtered = filtered.filter(article =>
                article.title.toLowerCase().includes(searchValue.toLowerCase()) ||
                article.description.toLowerCase().includes(searchValue.toLowerCase())
            );
        }

        this.setData({
            filteredArticles: filtered
        });
    },

    // 点击文章卡片
    onArticleClick(e) {
        const articleId = e.currentTarget.dataset.id;
        wx.navigateTo({
            url: `/pages/article-detail/index?id=${articleId}`
        });
    },

    // 底部导航切换
    onNavChange(e) {
        const index = e.currentTarget.dataset.index;

        this.setData({
            activeNavIndex: index
        });

        if (index === 0) {
            // 当前就是首页，不需要跳转
            return;
        } else {
            wx.showToast({
                title: '功能开发中',
                icon: 'none'
            });
        }
    }
}); 