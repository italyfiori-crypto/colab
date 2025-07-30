// vocabulary页面的单词本mock数据
const vocabularyBookData = {
    "day1": {
        title: "Day 1",
        totalWords: 8,
        masteredWords: 2,
        progress: 25,
        words: [
            {
                id: 1,
                word: "obtain",
                phonetic: "/əbˈteɪn/",
                translations: [
                    { partOfSpeech: "v.", meaning: "获得；得到" }
                ],
                status: "mastered",
                difficulty: "easy",
                frequency: "high",
                isLearned: false,
                isExpanded: false
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
                isLearned: false,
                isExpanded: false
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
                isLearned: false,
                isExpanded: false
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
                isLearned: false,
                isExpanded: false
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
                isLearned: false,
                isExpanded: false
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
                isLearned: false,
                isExpanded: false
            },
            {
                id: 7,
                word: "approach",
                phonetic: "/əˈprəʊtʃ/",
                translations: [
                    { partOfSpeech: "v.", meaning: "接近；靠近" },
                    { partOfSpeech: "n.", meaning: "方法；途径" }
                ],
                status: "learning",
                difficulty: "easy",
                frequency: "high",
                isLearned: false,
                isExpanded: false
            },
            {
                id: 8,
                word: "conduct",
                phonetic: "/ˈkɒndʌkt/",
                translations: [
                    { partOfSpeech: "v.", meaning: "进行；实施；指挥" },
                    { partOfSpeech: "n.", meaning: "行为；品行" }
                ],
                status: "new",
                difficulty: "medium",
                frequency: "medium",
                isLearned: false,
                isExpanded: false
            }
        ]
    },
    "day2": {
        title: "Day 2",
        totalWords: 10,
        masteredWords: 3,
        progress: 30,
        words: [
            {
                id: 9,
                word: "analyze",
                phonetic: "/ˈænəlaɪz/",
                translations: [
                    { partOfSpeech: "v.", meaning: "分析；分解" }
                ],
                status: "mastered",
                difficulty: "medium",
                frequency: "high",
                isLearned: false,
                isExpanded: false
            },
            {
                id: 10,
                word: "evaluate",
                phonetic: "/ɪˈvæljʊeɪt/",
                translations: [
                    { partOfSpeech: "v.", meaning: "评估；估价" }
                ],
                status: "learning",
                difficulty: "medium",
                frequency: "medium",
                isLearned: false,
                isExpanded: false
            },
            {
                id: 11,
                word: "generate",
                phonetic: "/ˈdʒɛnəreɪt/",
                translations: [
                    { partOfSpeech: "v.", meaning: "生成；产生" }
                ],
                status: "mastered",
                difficulty: "easy",
                frequency: "high",
                isLearned: false,
                isExpanded: false
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
                frequency: "medium",
                isLearned: false,
                isExpanded: false
            },
            {
                id: 13,
                word: "demonstrate",
                phonetic: "/ˈdɛmənstreɪt/",
                translations: [
                    { partOfSpeech: "v.", meaning: "演示；证明" }
                ],
                status: "mastered",
                difficulty: "medium",
                frequency: "high",
                isLearned: false,
                isExpanded: false
            },
            {
                id: 14,
                word: "navigate",
                phonetic: "/ˈnævɪɡeɪt/",
                translations: [
                    { partOfSpeech: "v.", meaning: "导航；航行" }
                ],
                status: "learning",
                difficulty: "medium",
                frequency: "medium",
                isLearned: false,
                isExpanded: false
            },
            {
                id: 15,
                word: "implement",
                phonetic: "/ˈɪmplɪment/",
                translations: [
                    { partOfSpeech: "v.", meaning: "实施；执行" },
                    { partOfSpeech: "n.", meaning: "工具；器具" }
                ],
                status: "new",
                difficulty: "hard",
                frequency: "high",
                isLearned: false,
                isExpanded: false
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
                frequency: "medium",
                isLearned: false,
                isExpanded: false
            },
            {
                id: 17,
                word: "facilitate",
                phonetic: "/fəˈsɪlɪteɪt/",
                translations: [
                    { partOfSpeech: "v.", meaning: "促进；使便利" }
                ],
                status: "new",
                difficulty: "hard",
                frequency: "medium",
                isLearned: false,
                isExpanded: false
            },
            {
                id: 18,
                word: "simulate",
                phonetic: "/ˈsɪmjʊleɪt/",
                translations: [
                    { partOfSpeech: "v.", meaning: "模拟；仿真" }
                ],
                status: "learning",
                difficulty: "medium",
                frequency: "low",
                isLearned: false,
                isExpanded: false
            }
        ]
    },
    "day3": {
        title: "Day 3",
        totalWords: 12,
        masteredWords: 4,
        progress: 33,
        words: [
            {
                id: 19,
                word: "accumulate",
                phonetic: "/əˈkjumjəˌleɪt/",
                translations: [
                    { partOfSpeech: "v.", meaning: "积累；堆积" }
                ],
                status: "mastered",
                difficulty: "medium",
                frequency: "medium",
                isLearned: false,
                isExpanded: false
            },
            {
                id: 20,
                word: "collaborate",
                phonetic: "/kəˈlæbəreɪt/",
                translations: [
                    { partOfSpeech: "v.", meaning: "合作；协作" }
                ],
                status: "mastered",
                difficulty: "medium",
                frequency: "high",
                isLearned: false,
                isExpanded: false
            },
            {
                id: 21,
                word: "eliminate",
                phonetic: "/ɪˈlɪməneɪt/",
                translations: [
                    { partOfSpeech: "v.", meaning: "消除；淘汰" }
                ],
                status: "learning",
                difficulty: "medium",
                frequency: "high",
                isLearned: false,
                isExpanded: false
            },
            {
                id: 22,
                word: "fundamental",
                phonetic: "/ˌfʌndəˈmɛntəl/",
                translations: [
                    { partOfSpeech: "adj.", meaning: "基本的；根本的" },
                    { partOfSpeech: "n.", meaning: "基本原理" }
                ],
                status: "mastered",
                difficulty: "medium",
                frequency: "high",
                isLearned: false,
                isExpanded: false
            },
            {
                id: 23,
                word: "investigate",
                phonetic: "/ɪnˈvɛstəɡeɪt/",
                translations: [
                    { partOfSpeech: "v.", meaning: "调查；研究" }
                ],
                status: "new",
                difficulty: "medium",
                frequency: "medium",
                isLearned: false,
                isExpanded: false
            },
            {
                id: 24,
                word: "manipulate",
                phonetic: "/məˈnɪpjəleɪt/",
                translations: [
                    { partOfSpeech: "v.", meaning: "操作；操纵" }
                ],
                status: "learning",
                difficulty: "hard",
                frequency: "medium",
                isLearned: false,
                isExpanded: false
            },
            {
                id: 25,
                word: "participate",
                phonetic: "/pɑrˈtɪsəpeɪt/",
                translations: [
                    { partOfSpeech: "v.", meaning: "参与；参加" }
                ],
                status: "mastered",
                difficulty: "easy",
                frequency: "high",
                isLearned: false,
                isExpanded: false
            },
            {
                id: 26,
                word: "substantial",
                phonetic: "/səbˈstænʃəl/",
                translations: [
                    { partOfSpeech: "adj.", meaning: "大量的；重要的" }
                ],
                status: "new",
                difficulty: "hard",
                frequency: "medium",
                isLearned: false,
                isExpanded: false
            },
            {
                id: 27,
                word: "technique",
                phonetic: "/tɛkˈnik/",
                translations: [
                    { partOfSpeech: "n.", meaning: "技术；技巧" }
                ],
                status: "learning",
                difficulty: "medium",
                frequency: "high",
                isLearned: false,
                isExpanded: false
            },
            {
                id: 28,
                word: "ultimate",
                phonetic: "/ˈʌltəmət/",
                translations: [
                    { partOfSpeech: "adj.", meaning: "最终的；极限的" },
                    { partOfSpeech: "n.", meaning: "终极；极限" }
                ],
                status: "new",
                difficulty: "medium",
                frequency: "medium",
                isLearned: false,
                isExpanded: false
            },
            {
                id: 29,
                word: "validate",
                phonetic: "/ˈvælɪdeɪt/",
                translations: [
                    { partOfSpeech: "v.", meaning: "验证；确认" }
                ],
                status: "learning",
                difficulty: "medium",
                frequency: "medium",
                isLearned: false,
                isExpanded: false
            },
            {
                id: 30,
                word: "withdraw",
                phonetic: "/wɪðˈdrɔ/",
                translations: [
                    { partOfSpeech: "v.", meaning: "撤回；提取" }
                ],
                status: "new",
                difficulty: "medium",
                frequency: "medium",
                isLearned: false,
                isExpanded: false
            }
        ]
    }
};

module.exports = vocabularyBookData;