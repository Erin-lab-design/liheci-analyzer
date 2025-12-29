# Liheci HFST Analyzer

Chinese separable verb (离合词) analyzer using HFST (Helsinki Finite-State Technology).

## 项目简介

本项目使用有限状态转导器（FST）技术来识别和分析中文离合词。离合词是现代汉语中一种特殊的词类，其特点是可以在两个语素之间插入其他成分，例如：

- 睡觉 → 睡了一个好觉 (SPLIT)
- 散步 → 散散步 (REDUP)
- 见面 → 跟朋友见面 (with PP)

本项目采用**两阶段HFST分析流程**：
- **Stage 1**: 识别 WHOLE/SPLIT 形式（所有131个词条）
- **Stage 2**: 验证 REDUP 重叠形式的有效性（55个AAB词条）

## 项目结构

```
liheci-analyzer/
├── data/                                      # 数据文件
│   ├── liheci_lexicon.csv                    # 离合词词典（131个词条）
│   ├── liheci_lexicon_ori.csv                # 原始词典
│   └── test_sentences.txt                    # 测试句子（325条）
│
├── scripts/                                   # Python 脚本
│   ├── 01.generate_liheci_split_xfst.py     # [Stage 1] 生成 WHOLE/SPLIT XFST
│   ├── liheci_split.xfst                     # [Stage 1] 生成的 XFST 规则
│   ├── liheci_split.analyser.hfst            # [Stage 1] 编译的分析器 (7MB)
│   ├── liheci_split.generator.hfst           # [Stage 1] 编译的生成器 (7MB)
│   ├── 03.liheci_run_hfst.py                # [Stage 1] 运行 Stage 1 分析
│   │
│   ├── 02.generate_liheci_redup_xfst.py     # [Stage 2] 生成 REDUP XFST
│   ├── liheci_redup.xfst                     # [Stage 2] 生成的 XFST 规则
│   ├── liheci_redup.analyser.hfst            # [Stage 2] 编译的分析器 (7MB)
│   ├── liheci_redup.generator.hfst           # [Stage 2] 编译的生成器 (7MB)
│   └── 04.liheci_validate_redup_hfst.py     # [Stage 2] 验证 REDUP 有效性
│
├── outputs/                                   # 输出结果
│   ├── liheci_hfst_outputs.tsv              # Stage 1 输出 (325 rows)
│   ├── liheci_hfst_outputs_filtered.tsv     # Stage 2 最终输出 (206 rows)
│   ├── liheci_hfst_run.log                  # Stage 1 运行日志
│   └── liheci_redup_validation.log          # Stage 2 验证日志
│
├── hfst-3.16.2/                              # HFST 工具包 (Windows)
├── pipeline.md                                # 流程说明文档
└── README.md                                  # 本文件
```

## 功能特性

- ✅ **Stage 1**: 识别离合词的 **WHOLE** 形式（连用）：睡觉
- ✅ **Stage 1**: 识别离合词的 **SPLIT** 形式（插入）：睡了一觉
- ✅ **Stage 2**: 验证 **REDUP** 重叠形式的有效性：散散步 ✓ / 结婚结婚婚 ✗
- ✅ 支持多种插入成分：体标记、数量短语、结果补语等
- ✅ 句子级别分析，自动定位离合词位置
- ✅ 双阶段验证，过滤无效重叠形式

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

### 完整流程（推荐）

运行两阶段分析流程：

```bash
# Stage 1: 识别 WHOLE/SPLIT 形式
python scripts/03.liheci_run_hfst.py

# 输出: outputs/liheci_hfst_outputs.tsv (325 rows)

# Stage 2: 验证 REDUP 有效性
python scripts/04.liheci_validate_redup_hfst.py

# 输出: outputs/liheci_hfst_outputs_filtered.tsv (206 rows)
```

### 从源码重新生成 XFST 文件

#### Stage 1: WHOLE/SPLIT Recognition

```bash
# 1. 生成 XFST 规则文件
python scripts/01.generate_liheci_split_xfst.py
# 输出: scripts/liheci_split.xfst

# 2. 编译为 HFST
cd scripts
hfst-xfst -F liheci_split.xfst
# 输出: liheci_split.analyser.hfst, liheci_split.generator.hfst

# 3. 运行分析
cd ..
python scripts/03.liheci_run_hfst.py
```

#### Stage 2: REDUP Validation

```bash
# 1. 生成 REDUP XFST 规则文件
python scripts/02.generate_liheci_redup_xfst.py
# 输出: scripts/liheci_redup.xfst

# 2. 编译为 HFST
cd scripts
hfst-xfst -F liheci_redup.xfst
# 输出: liheci_redup.analyser.hfst, liheci_redup.generator.hfst

# 3. 运行验证
cd ..
python scripts/04.liheci_validate_redup_hfst.py
```

### 使用命令行工具测试

```bash
# Stage 1: 测试 WHOLE/SPLIT 识别
echo "我昨天睡了一个好觉" | hfst-lookup scripts/liheci_split.analyser.hfst

# Stage 2: 测试 REDUP 识别
echo "散散步" | hfst-lookup scripts/liheci_redup.analyser.hfst
echo "见一见面" | hfst-lookup scripts/liheci_redup.analyser.hfst
```

## 输出格式

### Stage 1 输出 (`liheci_hfst_outputs.tsv`)

325 rows，包含所有识别出的 WHOLE 和 SPLIT 形式：

| sent_id | gold_stem | gold_label | sentence | lemma | type_tag | shape | is_redup | raw_analysis |
|---------|-----------|------------|----------|-------|----------|-------|----------|--------------|
| 1 | 睡觉 | True | 昨天晚上我睡了一个好觉。 | 睡觉 | Verb-Object | SPLIT | False | 睡觉+Lemma+Verb-Object+SPLIT |
| 2 | 散步 | True | 晚饭后我们去散散步。 | 散步 | Verb-Object | WHOLE | False | 散步+Lemma+Verb-Object+WHOLE |

### Stage 2 输出 (`liheci_hfst_outputs_filtered.tsv`)

206 rows，过滤了无效的重叠形式：

- **189 rows**: 非重叠形式（WHOLE 或 SPLIT）
- **17 rows**: 有效的重叠形式（REDUP）

**有效的 REDUP lemmas (17个)**：
散步, 见面, 聊天, 睡觉, 把脉, 洗澡, 鼓掌, 放假, 开会, 加班, 输液, 看病, 游泳, 排队, 散心

**被过滤的无效 REDUP lemmas (45个)**：
结婚, 离婚, 订婚, 分手, 放心, 担心, 灰心, 操心, 动心, 下课, 请假, 考试, 留学, 辞职, 生病, 住院, 鞠躬, 敬礼, 站岗, 受罪, 出院, 回家, 签名, 戒烟, 受伤, 扫兴, 接吻, 开枪, 受骗, 挨批, 干杯, 退休, 出事, 提醒, 出恭, 学习, 慷慨, 幽默, 滑稽, 军训, 体检, 同学, 告状, 请客

## 数据说明

### 离合词词典 (`data/liheci_lexicon.csv`)

包含 131 个离合词条目，字段包括：
- **Lemma**: 离合词原形
- **A**: 前半部分（head）
- **B**: 后半部分（tail）
- **Type**: 词类类型（Verb-Object, Modifier-Head, SimplexWord 等）
- **RedupPattern**: 重叠模式（'AAB' 表示可重叠，55个词条）
- **Pinyin**: 拼音
- **English Definition**: 英文释义
- **Notes**: 备注信息

### 测试句子 (`data/test_sentences.txt`)

包含 325 条测试句子，格式为 TAB 分隔：
```
sent_id	gold_stem	gold_label	sentence
1	睡觉	True	昨天晚上我睡了一个好觉。
2	散步	True	晚饭后我们去散散步。
```

## 技术细节

### XFST 规则生成

**关键技术要点**：
1. **字符格式化**: 中文字符必须空格分隔
   - 正确: `?* 散 散 步 ?*`
   - 错误: `?* 散散步 ?*`

2. **注释语法**: XFST 使用 `!` 而非 `#`
   - 正确: `! This is a comment`
   - 错误: `# This is a comment`

3. **保存顺序**: Generator 先保存，然后 invert 为 Analyser
   ```xfst
   regex LiheciRecognizer ;
   save stack filename.generator.hfst
   invert net
   save stack filename.analyser.hfst
   ```

### HFST 编译

```bash
hfst-xfst -F input.xfst
```

- `-F`: 使用 OpenFST tropical semiring（推荐）
- 输出: `.analyser.hfst` (7MB) 和 `.generator.hfst` (7MB)
- **Stage 1**: 663 states, 131 lemmas
- **Stage 2**: 225 states, 55 AAB lemmas

### HFST Lookup 输出格式

```
input\tanalysis\tweight
散散步	散步+Lemma+Verb-Object+REDUP	0.000000
```

- TAB 分隔: `[input]\t[analysis]\t[weight]`
- 无匹配返回: `input\tinput+?\tINF`

## 性能说明

- **Stage 1 分析时间**: 批处理模式，处理 325 个句子约需 1-2 分钟
- **Stage 2 验证时间**: 处理 124 个候选句子约需 10-20 秒
- **编译时间**: 
  - Stage 1 (131 lemmas): 约 30-60 秒
  - Stage 2 (55 lemmas): 约 10-20 秒
- **FST 大小**: 每个 .hfst 文件约 7MB

## 技术挑战与解决方案

### 问题 1: REDUP 识别失败
**症状**: 所有输入返回 `+?`（无匹配）

**根本原因**:
1. 缺少 `chars_with_space()` 函数进行字符格式化
2. 使用了错误的注释语法 (`#` 而非 `!`)
3. Generator/Analyser 保存顺序错误
4. HFST 输出解析逻辑有误

**解决方案**:
- 添加字符格式化函数
- 修正 XFST 语法
- 正确的保存顺序
- 正确解析 TAB 分隔的输出

详见 commit 1641d71

### 问题 2: 输出重复行
**症状**: 同一 (sent_id, lemma, shape) 出现多次

**解决方案**: 在 Stage 2 中按 (sent_id, lemma, shape) 去重
- 325 rows → 313 unique rows (去除 12 个重复)

## 已知限制

1. **REDUP 验证范围**: 仅支持 AAB 模式（散散步），不支持 ABAB 模式（调查调查）
2. **插入成分**: Stage 1 支持常见插入，但不分类（如体标记、量词等）
3. **语义验证**: 未实现语义层面的及物性检查、介词结构要求等
4. **处理速度**: HFST lookup 为串行处理，大规模数据可考虑并行化

## 更新日志

- **2024-12-29**: 
  - ✅ 实现两阶段 HFST 分析流程
  - ✅ Stage 1: WHOLE/SPLIT 识别（131 lemmas, 663 states）
  - ✅ Stage 2: REDUP 有效性验证（55 lemmas, 225 states）
  - ✅ 修复所有 XFST 生成和 HFST 输出解析问题
  - ✅ 验证 17 个有效 REDUP lemmas，过滤 45 个无效 lemmas
  - ✅ 最终输出 206 条有效识别结果
- **2024-12-09**: 初始版本，成功编译 HFST 文件
- **2024-12-27**: 更新词典，添加 RedupPattern 标注

## 参考文档

- [pipeline.md](pipeline.md) - 详细的流程说明和架构图
- [HFST - Helsinki Finite-State Technology](https://hfst.github.io/)
- Git Commit: [1641d71](https://github.com/Erin-lab-design/liheci-analyzer/commit/1641d71) - Stage 2 完整实现
