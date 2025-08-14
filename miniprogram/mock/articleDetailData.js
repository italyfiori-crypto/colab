const articleDetailData = {
    // 从字幕数据文件加载字幕数据
    loadSubtitlesFromSRT: function() {
        return new Promise((resolve, reject) => {
            try {
                // 导入字幕数据文件
                const { subtitleData } = require('./subtitleData.js');
                
                // 解析字幕数据
                const subtitles = this.parseSRTData(subtitleData);
                resolve(subtitles);
            } catch (error) {
                console.error('加载或解析字幕数据失败:', error);
                reject(new Error(`加载或解析字幕数据失败: ${error.message}`));
            }
        });
    },
    
    // 解析SRT格式字幕数据
    parseSRTData: function(data) {
        const subtitles = [];
        const blocks = data.trim().split(/\n\s*\n/); // 按空行分割字幕块

        for (let block of blocks) {
            const lines = block.trim().split('\n');
            if (lines.length >= 4) {
                const index = lines[0]; // 字幕序号
                const timeRange = lines[1]; // 时间范围
                const english = lines[2]; // 英文
                const chinese = lines[3]; // 中文

                // 解析开始时间
                const startTime = this.parseSRTTimeToSeconds(timeRange.split(' --> ')[0]);

                subtitles.push({
                    timeText: this.formatSecondsToMinutes(startTime),
                    time: startTime,
                    english: english,
                    chinese: chinese
                });
            }
        }

        return subtitles;
    },

    // 将SRT时间格式转换为秒 (HH:MM:SS,mmm)
    parseSRTTimeToSeconds: function(timeStr) {
        const parts = timeStr.split(':');
        const hours = parseInt(parts[0]) || 0;
        const minutes = parseInt(parts[1]) || 0;
        const secondsParts = parts[2].split(',');
        const seconds = parseInt(secondsParts[0]) || 0;
        const milliseconds = parseInt(secondsParts[1]) || 0;

        return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000;
    },

    // 将秒数格式化为分:秒格式
    formatSecondsToMinutes: function(seconds) {
        const minutes = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    },
    
    // 词汇表数据
    vocabulary: [
        {
            id: 1,
            word: 'escaping',
            phonetic: '/ɪˈskeɪpɪŋ/',
            translations: [
                { partOfSpeech: 'v.', meaning: '逃脱，逃避' }
            ],
            isFavorited: true
        },
        {
            id: 2,
            word: 'punishment',
            phonetic: '/ˈpʌnɪʃmənt/',
            translations: [
                { partOfSpeech: 'n.', meaning: '惩罚，处罚' }
            ],
            isFavorited: false
        },
        {
            id: 3,
            word: 'wizard',
            phonetic: '/ˈwɪzərd/',
            translations: [
                { partOfSpeech: 'n.', meaning: '巫师，魔法师' }
            ],
            isFavorited: false
        },
        {
            id: 4,
            word: 'mysterious',
            phonetic: '/mɪˈstɪəriəs/',
            translations: [
                { partOfSpeech: 'adj.', meaning: '神秘的，难解的' }
            ],
            isFavorited: true
        },
        {
            id: 5,
            word: 'adventure',
            phonetic: '/ədˈventʃər/',
            translations: [
                { partOfSpeech: 'n.', meaning: '冒险，奇遇' }
            ],
            isFavorited: false
        },
        {
            id: 6,
            word: 'infrastructure',
            phonetic: '/ˈɪnfrəstrʌktʃər/',
            translations: [
                { partOfSpeech: 'n.', meaning: '基础设施' }
            ],
            isFavorited: false
        },
        {
            id: 7,
            word: 'corruption',
            phonetic: '/kəˈrʌpʃən/',
            translations: [
                { partOfSpeech: 'n.', meaning: '腐败，贪污' }
            ],
            isFavorited: true
        },
        {
            id: 8,
            word: 'stability',
            phonetic: '/stəˈbɪləti/',
            translations: [
                { partOfSpeech: 'n.', meaning: '稳定性' }
            ],
            isFavorited: false
        }
    ]
}

module.exports = articleDetailData;