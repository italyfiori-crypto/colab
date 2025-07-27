Page({
    data: {
        // 文章信息
        articleId: null,
        title: '',

        // 字幕数据
        subtitles: [],
        currentIndex: 0,
        currentSubtitleId: 'subtitle-0',
        showChinese: true,

        // 音频控制
        isPlaying: false,
        currentTime: 0,
        duration: 240, // 4分钟，与mock音频长度匹配
        playSpeed: 1,
        speedOptions: [0.75, 1, 1.25, 1.5],

        // UI状态
        showSettings: false,
        isFavorited: false,

        // 图标
        playIcon: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTggNUwyMCAxMkw4IDE5VjVaIiBmaWxsPSIjNEE1QUU4Ii8+Cjwvc3ZnPgo=',
        pauseIcon: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTYgNkg5VjE4SDZWNlpNMTUgNkgxOFYxOEgxNVY2WiIgZmlsbD0iIzRBNUFFOCIvPgo8L3N2Zz4K',
        favoriteIcon: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEyIDIxLjM1TDEwLjU1IDIwLjAzQzUuNCAxNS4zNiAyIDEyLjI4IDIgOC41QzIgNS40MiA0LjQyIDMgNy41IDNDOS4yNCAzIDEwLjkxIDMuODEgMTIgNS4wOUMxMy4wOSAzLjgxIDE0Ljc2IDMgMTYuNSAzQzE5LjU4IDMgMjIgNS40MiAyMiA4LjVDMjIgMTIuMjggMTguNiAxNS4zNiAxMy40NSAyMC4wNEwxMiAyMS4zNVoiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgZmlsbD0ibm9uZSIvPgo8L3N2Zz4K',
        favoriteActiveIcon: 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjQiIGhlaWdodD0iMjQiIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEyIDIxLjM1TDEwLjU1IDIwLjAzQzUuNCAxNS4zNiAyIDEyLjI4IDIgOC41QzIgNS40MiA0LjQyIDMgNy41IDNDOS4yNCAzIDEwLjkxIDMuODEgMTIgNS4wOUMxMy4wOSAzLjgxIDE0Ljc2IDMgMTYuNSAzQzE5LjU4IDMgMjIgNS40MiAyMiA4LjVDMjIgMTIuMjggMTguNiAxNS4zNiAxMy40NSAyMC4wNEwxMiAyMS4zNVoiIGZpbGw9IiNGRjRCNEIiLz4KPC9zdmc+Cg=='
    },

    onLoad(options) {
        const articleId = options.id;
        this.setData({ articleId });

        // 设置标题
        wx.setNavigationBarTitle({
            title: '英语学习'
        });

        // 加载字幕数据
        this.loadSubtitleData();

        // 创建音频对象
        this.createAudioContext();

        // 加载收藏状态
        this.loadFavoriteStatus();
    },

    onReady() {
        // 页面渲染完成后，确保第一个字幕在顶部
        setTimeout(() => {
            this.setData({
                currentSubtitleId: ''  // 清空滚动目标，让列表保持在顶部
            });
        }, 100);
    },

    onUnload() {
        // 清理音频
        if (this.audioContext) {
            this.audioContext.destroy();
        }
        // 清理定时器
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
        }
    },

    // 加载字幕数据
    loadSubtitleData() {
        // 这里应该根据articleId获取对应的数据，现在使用solar.txt
        const mockData = `0:00
You're with Business Today.
您今天收看的是《今日商业》。
0:00
I'm Sally Bundock.
我是莎莉·邦多克。
0:02
In South Africa, uh, frequent power cuts is an issue that everyone's been battling with now for over 15 years.
在南非，频繁停电是15年来每个人都在努力解决的一个问题。
0:10
For those who have the means,they have been able to go off-rid.
对于那些有条件的人来说，他们已经能够摆脱困境。
0:13
They are kitted out with expensive solar systems and alternative energy sources.
它们配备了昂贵的太阳能系统和替代能源。
0:21
Now local companies are introducing pay as you go backup power systems which allows others in less welloff areas to to finally be able to do the same.
现在，当地公司正在引入按使用量付费的备用电源系统，这使得其他较不富裕地区的人们最终也能这样做。
0:29
From Johannesburg Pumza Flani has this report.
约翰内斯堡的PumzaFlani带来了此报道。
0:35
>> With stage six load shedding announced the last time>> in South Africa power cuts have become part of daily life.
随着南非宣布第六阶段限电，最后一次停电已成为日常生活的一部分。
0:41
Planned blackouts by escom the country's power utility have crippled businesses and homes for nearly 15 years.
该国电力公司ESCOM计划的停电已经导致企业和家庭陷入近15年的瘫痪。
0:49
At the heart of Escom's problems is aging infrastructure, poor planning for increasing energy demands,and a power utility besieged by corruption and mismanagement.
Escom问题的核心是基础设施老化、对日益增长的能源需求规划不力、以及电力公司深陷腐败和管理不善的泥潭。
1:02
In recent years, the few that can afford the high upfront costs have gone off-rid, installing solar systems, which can cost up to $16,000.
近年来，少数能够承担高额前期成本的人已经放弃了太阳能系统，安装了太阳能系统，其成本最高可达16,000美元。
1:13
This is money the majority of people here simply do not have.
这是这里大多数人根本就没有的钱。
1:18
Having regular power supply has increasingly become a privilege here.
拥有稳定的电力供应在这里越来越成为一种特权。
1:23
The power crisis has led to not only a stunted economy, but the loss of millions of jobs and opportunities in the townships.
电力危机不仅导致经济发展停滞，还导致乡镇失去数百万个工作岗位和机会。
1:31
Small businesses barely making profits are doing what they can to try and change the odds.
那些勉强盈利的小企业正在尽其所能试图改变现状。
1:40
In Kruger west of Johannesburg, Julius Gorbiting runs a small grocery shop,Aspaza.
在约翰内斯堡西部的克鲁格，朱利叶斯·戈比廷经营着一家名为Aspaza的小杂货店。
1:46
For more than a decade, it's helped to put food on the table until the lights went out.
十多年来，它一直帮助人们维持生计，直到灯熄灭为止。
1:53
>> It was affecting us directly to our pocket because you need to make an an alternative.
这直接影响到我们的钱包，因为我们需要做出选择。
2:00
We need a lot of electricity.
我们需要大量电力。
2:02
The fridges need to run every day.
冰箱需要每天运行。
2:04
If you don't have electricity, you can't even sell the frozen.
如果没有电，冷冻食品就卖不出去。
2:08
maybe will be rot.
可能会腐烂。
2:08
It's costing also you the money for that damages.
您还需要为这些损失支付金钱。
2:15
>> Then earlier this year, Julius installed a pay as you go solar system.
今年早些时候，朱利叶斯安装了按使用量付费的太阳能系统。
2:19
No more power cuts, no more spoiled goods.
不再有停电，不再有货物损坏。
2:22
He says it's helped save his business.
他说这有助于挽救他的生意。
2:29
The system comes from a South African startup.
该系统来自一家南非初创公司。
2:32
At the manufacturing plant,teams are hard at work to keep up with increasing demand.
在制造工厂，团队正在努力工作以满足不断增长的需求。
2:37
Solar may not be new,but this business's subscription model is, and it's created a way for township businesses and lower income households to also get in on the solar boom.
太阳能可能并不新鲜，但该业务的订阅模式却是新鲜事物，它为乡镇企业和低收入家庭创造了一种参与太阳能热潮的方式。
2:50
We had to look at the market across the different segments and start to create products that are fit for purpose and are affordable for that part of the market because part of our mission is to make sure that as many as many homeowners and small businesses have access to power, but not all of them on the affordability scale can afford the same standardized product.
我们必须审视不同细分市场的状况，并开始创造适合用途且该细分市场能够负担得起的产品，因为我们的使命之一是确保尽可能多的房主和小企业能够用上电，但并非所有有同等承受能力的人都能买得起相同的标准化产品。
3:07
So we had to do quite a bit of innovation and engineering to make sure that we provide that.
因此，我们必须进行大量的创新和工程，以确保我们能够提供这一点。
3:13
>> In the Moodley household, the move to solar was about something bigger.
对于穆德利家来说，使用太阳能具有更重要的意义。
3:16
For Mark's elderly mother, a constant supply of electricity for her oxygen machine is essential.
对于马克年迈的母亲来说，为她的氧气机持续供应电力至关重要。
3:23
In the past, being without power has been life-threatening.
过去，断电会危及生命。
3:29
>> It's been a lifesaver.
这真是救命稻草。
3:30
And even now with the solar on, it like adds it value.
即使现在有了太阳能，它的价值也增加了。
3:33
cuz I don't have to go around.
因为我不需要到处走动。
3:38
Oxygen doesn't get depleted and uh I don't have to rush her into emergency when there's no electricity.
氧气不会耗尽，而且当没有电的时候，我也不必急着送她去急救。
3:49
>> As South Africa's energy crisis drags on in a country drenched with sunshine,solutions like these are not only offering power and stability, but may bring back a glimmer of hope.
随着南非这个阳光充沛的国家能源危机持续蔓延，此类解决方案不仅能提供电力和稳定，还能带来一线希望。
4:00
Pum Zaflani, BBC News, Johannesburg.
普姆·扎夫拉尼（PumZaflani），BBC新闻，约翰内斯堡。`;

        const subtitles = this.parseSubtitleData(mockData);
        this.setData({ subtitles });
    },

    // 解析字幕数据
    parseSubtitleData(data) {
        const lines = data.trim().split('\n');
        const subtitles = [];

        for (let i = 0; i < lines.length; i += 3) {
            if (i + 2 < lines.length) {
                const timeText = lines[i];
                const english = lines[i + 1];
                const chinese = lines[i + 2];

                // 转换时间为秒
                const timeSeconds = this.parseTimeToSeconds(timeText);

                subtitles.push({
                    timeText,
                    time: timeSeconds,
                    english,
                    chinese
                });
            }
        }

        return subtitles;
    },

    // 将时间字符串转换为秒
    parseTimeToSeconds(timeStr) {
        const parts = timeStr.split(':');
        const minutes = parseInt(parts[0]) || 0;
        const seconds = parseInt(parts[1]) || 0;
        return minutes * 60 + seconds;
    },

    // 创建音频上下文
    createAudioContext() {
        this.audioContext = wx.createInnerAudioContext();
        this.audioContext.src = '/mock/solar.mp3';
        this.audioContext.autoplay = false;

        // 监听音频事件
        this.audioContext.onCanplay(() => {
            console.log('音频可以播放');
        });

        this.audioContext.onPlay(() => {
            this.setData({ isPlaying: true });
            this.startUpdateTimer();
        });

        this.audioContext.onPause(() => {
            this.setData({ isPlaying: false });
            this.stopUpdateTimer();
        });

        this.audioContext.onStop(() => {
            this.setData({ isPlaying: false });
            this.stopUpdateTimer();
        });

        this.audioContext.onEnded(() => {
            this.setData({ isPlaying: false });
            this.stopUpdateTimer();
        });

        this.audioContext.onError((error) => {
            console.error('音频播放错误:', error);
            wx.showToast({
                title: '音频加载失败',
                icon: 'none'
            });
        });
    },

    // 开始更新定时器
    startUpdateTimer() {
        this.updateTimer = setInterval(() => {
            if (this.audioContext) {
                const currentTime = this.audioContext.currentTime;
                this.setData({ currentTime });
                this.updateCurrentSubtitle(currentTime);
            }
        }, 100);
    },

    // 停止更新定时器
    stopUpdateTimer() {
        if (this.updateTimer) {
            clearInterval(this.updateTimer);
            this.updateTimer = null;
        }
    },

    // 更新当前字幕
    updateCurrentSubtitle(currentTime) {
        const { subtitles } = this.data;
        let newIndex = 0;

        for (let i = 0; i < subtitles.length; i++) {
            if (currentTime >= subtitles[i].time) {
                newIndex = i;
            } else {
                break;
            }
        }

        if (newIndex !== this.data.currentIndex) {
            this.setData({
                currentIndex: newIndex,
                currentSubtitleId: newIndex === 0 ? '' : `subtitle-${newIndex}`
            });
        }
    },

    // 播放/暂停
    onPlayPause() {
        if (this.data.isPlaying) {
            this.audioContext.pause();
        } else {
            this.audioContext.play();
        }
    },

    // 上一句
    onPrevious() {
        const { currentIndex, subtitles } = this.data;
        if (currentIndex > 0) {
            const newIndex = currentIndex - 1;
            const time = subtitles[newIndex].time;
            this.audioContext.seek(time);
            this.setData({
                currentIndex: newIndex,
                currentSubtitleId: newIndex === 0 ? '' : `subtitle-${newIndex}`,
                currentTime: time
            });
        }
    },

    // 下一句
    onNext() {
        const { currentIndex, subtitles } = this.data;
        if (currentIndex < subtitles.length - 1) {
            const newIndex = currentIndex + 1;
            const time = subtitles[newIndex].time;
            this.audioContext.seek(time);
            this.setData({
                currentIndex: newIndex,
                currentSubtitleId: `subtitle-${newIndex}`,
                currentTime: time
            });
        }
    },

    // 点击字幕
    onSubtitleTap(e) {
        const index = e.currentTarget.dataset.index;
        const time = this.data.subtitles[index].time;
        this.audioContext.seek(time);
        this.setData({
            currentIndex: index,
            currentSubtitleId: index === 0 ? '' : `subtitle-${index}`,
            currentTime: time
        });
    },

    // 进度条改变
    onProgressChange(e) {
        const time = e.detail.value;
        this.audioContext.seek(time);
        this.setData({ currentTime: time });
        this.updateCurrentSubtitle(time);
    },

    onProgressChanging(e) {
        const time = e.detail.value;
        this.setData({ currentTime: time });
        this.updateCurrentSubtitle(time);
    },

    // 收藏
    onFavorite() {
        const isFavorited = !this.data.isFavorited;
        this.setData({ isFavorited });

        // 保存收藏状态到本地存储
        wx.setStorageSync(`favorite_${this.data.articleId}`, isFavorited);

        wx.showToast({
            title: isFavorited ? '已收藏' : '已取消收藏',
            icon: 'success',
            duration: 1000
        });
    },

    // 加载收藏状态
    loadFavoriteStatus() {
        const isFavorited = wx.getStorageSync(`favorite_${this.data.articleId}`) || false;
        this.setData({ isFavorited });
    },

    // 打开设置
    onSettings() {
        this.setData({ showSettings: true });
    },

    // 关闭设置
    onCloseSettings() {
        this.setData({ showSettings: false });
    },

    // 阻止冒泡
    stopPropagation() {
        // 空函数，阻止冒泡
    },

    // 播放速度改变
    onSpeedChange(e) {
        const speed = parseFloat(e.currentTarget.dataset.speed);
        this.setData({ playSpeed: speed });
        this.audioContext.playbackRate = speed;

        wx.showToast({
            title: `播放速度: ${speed}x`,
            icon: 'none',
            duration: 1000
        });
    },

    // 字幕模式改变
    onSubtitleModeChange(e) {
        const mode = e.currentTarget.dataset.mode;
        const showChinese = mode === 'both';
        this.setData({ showChinese });

        wx.showToast({
            title: showChinese ? '双语模式' : '英语模式',
            icon: 'none',
            duration: 1000
        });
    }
}); 