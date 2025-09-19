import requests
import os

# 输出文件夹
output_dir = "ebooks"
os.makedirs(output_dir, exist_ok=True)

# 书籍列表：英文名, 中文名, Gutenberg 下载链接, 出版年份
books = [
    ("Alice’s Adventures in Wonderland", "爱丽丝梦游仙境", "https://www.gutenberg.org/files/11/11-0.txt", 1865),
    ("Through the Looking-Glass", "爱丽丝镜中奇遇记", "https://www.gutenberg.org/files/12/12-0.txt", 1871),
    ("Grimm’s Fairy Tales", "格林童话", "https://www.gutenberg.org/files/2591/2591-0.txt", 1812),
    ("Andersen’s Fairy Tales", "安徒生童话", "https://www.gutenberg.org/files/1597/1597-0.txt", 1835),
    ("The Jungle Book", "丛林之书", "https://www.gutenberg.org/files/236/236-0.txt", 1894),
    ("Just So Stories", "正是如此的故事", "https://www.gutenberg.org/files/2781/2781-0.txt", 1902),
    ("The Wonderful Wizard of Oz", "绿野仙踪", "https://www.gutenberg.org/files/55/55-0.txt", 1900),
    ("Peter and Wendy", "彼得潘", "https://www.gutenberg.org/files/16/16-0.txt", 1911),
    ("Pinocchio", "木偶奇遇记", "https://www.gutenberg.org/files/500/500-0.txt", 1883),
    ("The Secret Garden", "秘密花园", "https://www.gutenberg.org/files/17396/17396-0.txt", 1911),
    ("A Little Princess", "小公主", "https://www.gutenberg.org/files/146/146-0.txt", 1905),
    ("Pollyanna", "波莉安娜", "https://www.gutenberg.org/files/1450/1450-0.txt", 1913),
    ("Five Children and It", "五个孩子和沙精", "https://www.gutenberg.org/files/778/778-0.txt", 1902),
    ("The Railway Children", "铁路边的孩子们", "https://www.gutenberg.org/files/1874/1874-0.txt", 1906),
    ("Heidi", "海蒂", "https://www.gutenberg.org/files/1448/1448-0.txt", 1880),
    ("Treasure Island", "金银岛", "https://www.gutenberg.org/files/120/120-0.txt", 1883),
    ("The Adventures of Tom Sawyer", "汤姆·索亚历险记", "https://www.gutenberg.org/files/74/74-0.txt", 1876),
    ("Adventures of Huckleberry Finn", "哈克贝利·费恩历险记", "https://www.gutenberg.org/files/76/76-0.txt", 1884),
    ("Robinson Crusoe", "鲁滨逊漂流记", "https://www.gutenberg.org/files/521/521-0.txt", 1719),
    ("Gulliver’s Travels", "格列佛游记", "https://www.gutenberg.org/files/829/829-0.txt", 1726),
    ("Pride and Prejudice", "傲慢与偏见", "https://www.gutenberg.org/files/1342/1342-0.txt", 1813),
    ("Jane Eyre", "简·爱", "https://www.gutenberg.org/files/1260/1260-0.txt", 1847),
    ("Wuthering Heights", "呼啸山庄", "https://www.gutenberg.org/files/768/768-0.txt", 1847),
    ("David Copperfield", "大卫·科波菲尔", "https://www.gutenberg.org/files/766/766-0.txt", 1850),
    ("Oliver Twist", "雾都孤儿", "https://www.gutenberg.org/files/730/730-0.txt", 1837),
    ("Great Expectations", "远大前程", "https://www.gutenberg.org/files/1400/1400-0.txt", 1861),
    ("The Picture of Dorian Gray", "道林·格雷的画像", "https://www.gutenberg.org/files/174/174-0.txt", 1890),
    ("Sherlock Holmes", "福尔摩斯探案集", "https://www.gutenberg.org/files/1661/1661-0.txt", 1887),
    ("Dracula", "德古拉", "https://www.gutenberg.org/files/345/345-0.txt", 1897),
    ("Frankenstein", "科学怪人", "https://www.gutenberg.org/files/84/84-0.txt", 1818),
    ("The Time Machine", "时间机器", "https://www.gutenberg.org/files/35/35-0.txt", 1895),
    ("The War of the Worlds", "世界大战", "https://www.gutenberg.org/files/36/36-0.txt", 1898),
    ("Twenty Thousand Leagues Under the Seas", "海底两万里", "https://www.gutenberg.org/files/164/164-0.txt", 1870),
    ("Around the World in Eighty Days", "八十天环游地球", "https://www.gutenberg.org/files/103/103-0.txt", 1873),
    ("A Journey to the Centre of the Earth", "地心游记", "https://www.gutenberg.org/files/18857/18857-0.txt", 1864),
    ("Angus and the Ducks", "安格斯与鸭子", "https://www.gutenberg.org/files/18252/18252-0.txt", 1889)
]


for title_en, title_cn, url, year in books:
    filename = f"{year}_{title_cn}.txt"
    filepath = os.path.join(output_dir, filename)
    
    try:
        print(f"Downloading {title_en}...")
        r = requests.get(url)
        r.raise_for_status()
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(r.text)
        print(f"Saved to {filepath}")
    except Exception as e:
        print(f"Failed to download {title_en}: {e}")
