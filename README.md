# Liheci HFST Analyzer

Chinese separable verb (离合词) analyzer using HFST (Helsinki Finite-State Technology).

## 项目简介

本项目使用有限状态转导器（FST）技术来识别和分析中文离合词。离合词是现代汉语中一种特殊的词类，其特点是可以在两个语素之间插入其他成分，例如：

- 睡觉 → 睡了一个好觉 (SPLIT)
- 散步 → 散散步 (REDUP)
- 见面 → 跟朋友见面 (with PP)

## 项目结构

```
liheci_project/
├── data/                           # 数据文件
│   ├── liheci_lexicon.csv         # 离合词词典（131个词条）
│   └── test_sentences.txt         # 测试句子
├── scripts/                        # Python 脚本
│   ├── 01.generate_liheci_split_xfst.py  # 生成 XFST 规则文件
│   ├── 02.liheci_split.xfst              # 12月9日成功的 XFST 版本
│   └── 03.liheci_run_hfst.py            # 运行 HFST 分析
├── fst_result_12.9/               # 编译好的 HFST 文件（12月9日版本）
│   ├── liheci_split.analyser.hfst
│   └── liheci_split.generator.hfst
└── outputs/                        # 输出结果
    └── logs/                       # 运行日志
```

## 功能特性

- ✅ 识别离合词的 **WHOLE** 形式（连用）：睡觉
- ✅ 识别离合词的 **SPLIT** 形式（插入）：睡了一觉
- ✅ 识别离合词的 **REDUP** 形式（重叠）：散散步
- ✅ 支持多种插入成分：体标记、数量短语、代词、结果补语等
- ✅ 句子级别分析，自动定位离合词位置

## 环境要求

- Python 3.7+
- HFST toolkit (hfst-xfst, hfst-lookup)

## 安装

### 1. 安装 HFST

**macOS:**
```bash
brew install hfst
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt-get install hfst

# 或从源码编译
git clone https://github.com/hfst/hfst.git
cd hfst
./configure
make
sudo make install
```

### 2. 克隆项目

```bash
git clone https://github.com/YOUR_USERNAME/liheci-hfst-analyzer.git
cd liheci-hfst-analyzer
```

### 3. 创建虚拟环境（可选）

```bash
python3 -m venv hfst-env
source hfst-env/bin/activate  # macOS/Linux
# 或 hfst-env\Scripts\activate  # Windows
```

## 使用方法

### 方法 1：使用已编译的 HFST 文件（推荐）

直接使用 `fst_result_12.9/` 目录下已经编译好的 HFST 文件：

```bash
python3 scripts/03.liheci_run_hfst.py
```

### 方法 2：从源码重新编译

#### 步骤 1：生成 XFST 规则文件

```bash
python3 scripts/01.generate_liheci_split_xfst.py
```

这会生成 `liheci_split.xfst` 文件。

#### 步骤 2：编译 XFST 为 HFST

```bash
hfst-xfst < liheci_split.xfst
```

这会生成：
- `liheci_split.generator.hfst` - 生成器
- `liheci_split.analyser.hfst` - 分析器

#### 步骤 3：运行分析

```bash
python3 scripts/03.liheci_run_hfst.py
```

### 使用命令行工具测试

```bash
# 单个句子测试
echo "我昨天睡了一个好觉" | hfst-lookup fst_result_12.9/liheci_split.analyser.hfst

# 批量测试
cat test_sentences.txt | hfst-lookup fst_result_12.9/liheci_split.analyser.hfst
```

## 输出格式

分析结果保存在 `liheci_hfst_outputs_retest.tsv` 文件中，格式为：

| sent_id | gold_stem | gold_label | sentence | lemma | type_tag | shape | is_redup | raw_analysis |
|---------|-----------|------------|----------|-------|----------|-------|----------|--------------|
| 1 | 睡觉 | True | 昨天晚上我睡了一个好觉。 | 睡觉 | Verb-Object | SPLIT | False | 睡觉+Lemma+Verb-Object+SPLIT |

## 数据说明

### 离合词词典 (`data/liheci_lexicon.csv`)

包含 131 个离合词条目，字段包括：
- **Lemma**: 离合词原形
- **A**: 前半部分（head）
- **B**: 后半部分（tail）
- **Type**: 词类类型（Verb-Object, Modifier-Head, SimplexWord 等）
- **Pinyin**: 拼音
- **English Definition**: 英文释义
- **Notes**: 备注信息

### 测试句子 (`data/test_sentences.txt`)

包含测试句子，格式为 TAB 分隔：
```
sent_id	gold_stem	gold_label	sentence
1	睡觉	True	昨天晚上我睡了一个好觉。
```

## 性能说明

- 每个句子的分析时间：约 **1-2 秒**
- 使用的是 HFST "slow lookup" 模式（OpenFST 格式）
- 对于大规模批量处理，建议考虑优化或分批编译

## 已知问题

1. **编译时间长**：如果一次性编译所有 131 个词条（特别是包含大量 Redup 模式时），编译可能需要 1-2 小时甚至失败
2. **查询速度**：当前版本每句查询需要 1-2 秒，对于大规模数据可能较慢
3. **推荐方案**：使用已编译的 `fst_result_12.9/` 文件，或考虑分批编译策略

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

MIT License

## 参考资料

- [HFST - Helsinki Finite-State Technology](https://hfst.github.io/)
- [离合词研究相关文献]

## 作者

[Your Name]

## 更新日志

- **2024-12-09**: 初始版本，成功编译 128 个词条的 HFST 文件
- **2024-12-27**: 更新词典，添加 Redup 模式支持
