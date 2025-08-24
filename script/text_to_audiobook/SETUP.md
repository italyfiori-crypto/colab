# 环境配置说明

## Python依赖安装

本项目需要安装以下库用于文本处理功能：

### 必需依赖

1. **安装NLTK库**（备用句子分割器）
   ```bash
   pip3 install nltk
   ```

2. **安装pySBD库**（主要句子分割器，推荐）
   ```bash
   pip3 install pysbd
   ```

3. **安装spaCy库**（短句拆分功能）
   ```bash
   pip3 install spacy
   ```

4. **下载spaCy英文模型**
   ```bash
   python3 -m spacy download en_core_web_sm
   ```

5. **下载NLTK数据包**
   ```bash
   python3 -c "import nltk; nltk.download('punkt')"
   ```

### 验证安装

1. **验证NLTK安装**
   ```python
   import nltk
   print("NLTK版本:", nltk.__version__)
   ```

2. **验证pySBD安装**
   ```python
   import pysbd
   seg = pysbd.Segmenter(language="en", clean=False)
   test_text = 'He said, "Oh dear! Oh dear! I shall be late!"'
   sentences = seg.segment(test_text)
   print("pySBD分割结果:", sentences)
   ```

### 故障排除

**问题1**: 网络问题导致punkt数据包下载失败
- 解决方案: 可以手动下载punkt数据包到NLTK数据目录

**问题2**: 权限问题
- 解决方案: 使用虚拟环境或添加`--user`参数安装

**问题3**: 代理环境下载失败
- 解决方案: 配置代理或使用离线安装包

## 配置说明

### 句子分割器选择

项目支持两种句子分割器，可在 `config.json` 中配置：

```json
{
  "sentence": {
    "output_subdir": "sentences",
    "segmenter": "pysbd",      // 'pysbd' 或 'nltk'
    "language": "en",          // 语言设置
    "clean": false             // 是否清理文本
  }
}
```

- **pySBD** (推荐): 专门为句子边界检测设计，对引号对话处理更好
- **NLTK**: 传统方案，作为备用选择

## 使用说明

安装完成后，句子拆分功能将自动集成到主流程中：

```bash
python3 split_chapters.py data/book.txt
```

输出目录结构：
```
output/
├── chapters/       # 章节拆分结果
├── sub_chapters/   # 子章节拆分结果  
└── sentences/      # 句子拆分结果
```

### 改进效果

使用pySBD后，引号对话将被正确处理：
- 之前: `"Oh dear!"` `Oh dear!"` `"I shall be late!"` (3个句子)
- 现在: `"Oh dear! Oh dear! I shall be late!"` (1个完整句子)