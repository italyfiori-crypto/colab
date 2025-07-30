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
                word: "obtain",
                phonetic: "/əbˈteɪn/",
                translations: [
                    { partOfSpeech: "v.", meaning: "获得；得到" }
                ],
                status: "mastered", // mastered, learning, new
                difficulty: "easy",
                frequency: "high",
                isFavorited: true
            },
            {
                id: 2,
                word: "character",
                phonetic: "/ˈkærəktə(r)/",
                translations: [
                    { partOfSpeech: "n.", meaning: "人物角色；性格；特点；文字" }
                ],
                status: "learning",
                difficulty: "medium",
                frequency: "medium",
                isFavorited: false
            },
            {
                id: 3,
                word: "effective",
                phonetic: "/ɪˈfektɪv/",
                translations: [
                    { partOfSpeech: "adj.", meaning: "有效的；起作用的" }
                ],
                status: "new",
                difficulty: "easy",
                frequency: "high",
                isFavorited: false
            },
            {
                id: 4,
                word: "crude",
                phonetic: "/kruːd/",
                translations: [
                    { partOfSpeech: "adj.", meaning: "粗糙的；未加工的" },
                    { partOfSpeech: "n.", meaning: "原油" }
                ],
                status: "learning",
                difficulty: "medium",
                frequency: "medium",
                isFavorited: false
            },
            {
                id: 5,
                word: "poll",
                phonetic: "/pəʊl/",
                translations: [
                    { partOfSpeech: "n.", meaning: "民意调查；投票" },
                    { partOfSpeech: "v.", meaning: "对...进行民意调查" }
                ],
                status: "mastered",
                difficulty: "easy",
                frequency: "high",
                isFavorited: true
            },
            {
                id: 6,
                word: "consult",
                phonetic: "/kənˈsʌlt/",
                translations: [
                    { partOfSpeech: "v.", meaning: "咨询；请教；查阅" }
                ],
                status: "new",
                difficulty: "medium",
                frequency: "medium",
                isFavorited: false
            },
            {
                id: 7,
                word: "approach",
                phonetic: "/əˈprəʊtʃ/",
                translations: [
                    { partOfSpeech: "v.", meaning: "接近；靠近" },
                    { partOfSpeech: "n.", meaning: "方法；途径" }
                ],
                status: "mastered",
                difficulty: "easy",
                frequency: "high",
                isFavorited: true
            },
            {
                id: 8,
                word: "conduct",
                phonetic: "/ˈkɒndʌkt/",
                translations: [
                    { partOfSpeech: "v.", meaning: "进行；实施；指挥" },
                    { partOfSpeech: "n.", meaning: "行为；品行" }
                ],
                status: "learning",
                difficulty: "medium",
                frequency: "medium",
                isFavorited: false
            },
            {
                id: 9,
                word: "analyze",
                phonetic: "/ˈænəlaɪz/",
                translations: [
                    { partOfSpeech: "v.", meaning: "分析；分解" }
                ],
                status: "new",
                difficulty: "hard",
                frequency: "low",
                isFavorited: false
            },
            {
                id: 10,
                word: "evaluate",
                phonetic: "/ɪˈvæljʊeɪt/",
                translations: [
                    { partOfSpeech: "v.", meaning: "评估；估价" }
                ],
                status: "learning",
                difficulty: "hard",
                frequency: "low",
                isFavorited: false
            },
            {
                id: 11,
                word: "generate",
                phonetic: "/ˈdʒɛnəreɪt/",
                translations: [
                    { partOfSpeech: "v.", meaning: "生成；产生" }
                ],
                status: "mastered",
                difficulty: "medium",
                frequency: "high",
                isFavorited: true
            },
            {
                id: 12,
                word: "integrate",
                phonetic: "/ɪnˈtɛɡreɪt/",
                translations: [
                    { partOfSpeech: "v.", meaning: "集成；整合" }
                ],
                status: "new",
                difficulty: "hard",
                frequency: "low",
                isFavorited: false
            },
            {
                id: 13,
                word: "iterate",
                phonetic: "/ɪˈtɛrət/",
                translations: [
                    { partOfSpeech: "v.", meaning: "迭代；重复" }
                ],
                status: "learning",
                difficulty: "hard",
                frequency: "low",
                isFavorited: false
            },
            {
                id: 14,
                word: "navigate",
                phonetic: "/ˈnævɪɡeɪt/",
                translations: [
                    { partOfSpeech: "v.", meaning: "导航；航行" }
                ],
                status: "mastered",
                difficulty: "medium",
                frequency: "high",
                isFavorited: true
            },
            {
                id: 15,
                word: "orient",
                phonetic: "/ˈɔːriənt/",
                translations: [
                    { partOfSpeech: "v.", meaning: "定向；面向" }
                ],
                status: "new",
                difficulty: "hard",
                frequency: "low",
                isFavorited: false
            },
            {
                id: 16,
                word: "prioritize",
                phonetic: "/praɪˈɔːrɪtaɪz/",
                translations: [
                    { partOfSpeech: "v.", meaning: "优先考虑；排序" }
                ],
                status: "learning",
                difficulty: "hard",
                frequency: "low",
                isFavorited: false
            },
            {
                id: 17,
                word: "reorganize",
                phonetic: "/riːˈɔːɡənaɪz/",
                translations: [
                    { partOfSpeech: "v.", meaning: "重新组织；改组" }
                ],
                status: "mastered",
                difficulty: "hard",
                frequency: "low",
                isFavorited: true
            },
            {
                id: 18,
                word: "simulate",
                phonetic: "/ˈsɪmjʊleɪt/",
                translations: [
                    { partOfSpeech: "v.", meaning: "模拟；仿真" }
                ],
                status: "new",
                difficulty: "hard",
                frequency: "low",
                isFavorited: false
            }
        ]
    }
};

module.exports = vocabularyData; 