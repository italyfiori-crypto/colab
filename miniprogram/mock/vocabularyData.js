// article-vocabulary页面的mock数据
const vocabularyData = {
    "harry-potter-1": {
        title: "哈利·波特与魔法石",
        totalWords: 236,
        masteredWords: 89,
        progress: 38,
        words: [
            {
                id: 1,
                word: "escaping",
                phonetic: "/ɪˈskeɪpɪŋ/",
                translation: "逃脱，逃避",
                status: "mastered", // mastered, learning, new
                difficulty: "easy",
                frequency: "high",
                isFavorited: true
            },
            {
                id: 2,
                word: "punishment",
                phonetic: "/ˈpʌnɪʃmənt/",
                translation: "惩罚，处罚",
                status: "learning",
                difficulty: "medium",
                frequency: "medium",
                isFavorited: false
            },
            {
                id: 3,
                word: "wizard",
                phonetic: "/ˈwɪzərd/",
                translation: "巫师，魔法师",
                status: "new",
                difficulty: "easy",
                frequency: "high",
                isFavorited: false
            },
            {
                id: 4,
                word: "mysterious",
                phonetic: "/mɪˈstɪəriəs/",
                translation: "神秘的，不可思议的",
                status: "learning",
                difficulty: "medium",
                frequency: "medium",
                isFavorited: false
            },
            {
                id: 5,
                word: "ordinary",
                phonetic: "/ˈɔːrdɪneri/",
                translation: "普通的，平凡的",
                status: "mastered",
                difficulty: "easy",
                frequency: "high",
                isFavorited: true
            },
            {
                id: 6,
                word: "ancient",
                phonetic: "/ˈeɪnʃənt/",
                translation: "古老的，古代的",
                status: "new",
                difficulty: "medium",
                frequency: "medium",
                isFavorited: false
            },
            {
                id: 7,
                word: "powerful",
                phonetic: "/ˈpaʊərfəl/",
                translation: "强大的，有力的",
                status: "mastered",
                difficulty: "easy",
                frequency: "high",
                isFavorited: true
            },
            {
                id: 8,
                word: "creature",
                phonetic: "/ˈkriːtʃər/",
                translation: "生物，动物",
                status: "learning",
                difficulty: "medium",
                frequency: "medium",
                isFavorited: false
            }
        ]
    }
};

module.exports = vocabularyData; 