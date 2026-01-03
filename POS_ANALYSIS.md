# POS-Based Validation Rules Analysis

Based on HanLP POS tagging results from 159 liheci instances.

## 1. Liheci Type Distribution

| Type | Count | Percentage |
|------|-------|------------|
| **Verb-Object** | 141 | 88.7% |
| Modifier-Head | 9 | 5.7% |
| PseudoV-O | 6 | 3.8% |
| SimplexWord | 3 | 1.9% |

## 2. POS Patterns by Liheci Type

### 2.1 Verb-Object (动宾式, 88.7%)

**HEAD POS Distribution:**
- VV (verb): 137 (97.2%) ← **DOMINANT**
- NN (noun): 3 (2.1%)
- NT (temporal noun): 1 (0.7%)

**TAIL POS Distribution:**
- NN (noun): 109 (77.3%) ← **DOMINANT**
- VV (verb): 28 (19.9%) ← **大多为WHOLE/REDUP形式**
- M (measure): 2 (1.4%)
- AD (adverb): 1 (0.7%)
- VA (adj-verb): 1 (0.7%)

**TAIL=VV (20%) Breakdown (28 cases analyzed):**
- ✅ **WHOLE forms** (17, 61%): 睡觉/VV, 见面/VV, 打仗/VV, 吹牛/VV, 结婚/VV, 说话/VV, 生病/VV, 下班/VV, 挂号/VV, 回家/VV, 退休/VV, 吵架/VV... → HanLP将未分离整词标注为单个VV token，**合法**
- ✅ **Reduplication** (9, 32%): 散散步/VV, 见一见面/VV, 聊聊天/VV, 睡睡觉/VV, 把把脉/VV, 洗洗澡/VV, 散散心/VV → 重叠式自然产生VV标签，**合法**
- ⚠️ **Suspicious** (2, 7%): 理发(发/VV应为NN), 退休(休/VV应为NN) → 可能是HanLP标注误差

**Validation Rules for Verb-Object:**
- ✅ **VALID**: HEAD=VV, TAIL=NN (主要模式, ~77%)
- ✅ **VALID**: HEAD=VV, TAIL=VV + (WHOLE形式 或 is_redup=True) → 合法模式
- ⚠️ **SUSPICIOUS**: HEAD=VV, TAIL=VV + SPLIT + not_redup → 可能标注误差，降低置信度
- ❌ **REJECT**: TAIL ∈ {AD, P, CS, CC} → 假阳性（如"大便"句中便/AD）
- ❌ **REJECT**: HEAD=VA, TAIL=VA → 属于Modifier-Head，非Verb-Object

### 2.2 Modifier-Head (偏正式, 5.7%)

**HEAD POS Distribution (9 cases):**
- NN (noun): 3 (33.3%)
- VV (verb): 3 (33.3%)
- VA (adj-verb): 2 (22.2%) ← **KEY MARKER**
- AD (adverb): 1 (11.1%)

**TAIL POS Distribution:**
- NN (noun): 5 (55.6%)
- VA (adj-verb): 2 (22.2%) ← **KEY MARKER**
- VV (verb): 2 (22.2%)

**Examples by POS Pattern:**
- **VA→VA**: 小便(小/VA 便/VA), 大便(大/VA 便/VA) ← 真正离合词
- **VV→VV**: 军训(军/VV 训/VV), 暂停(暂/VV 停/VV)
- **VV→NN**: 体检(体/VV 检/NN)
- **AD→NN**: 同学(同/AD 学/NN)
- **NN→NN**: 小便宜/NN, 大便宜/NN ← **假阳性**（整词误识别）

**Validation Rules for Modifier-Head:**
- ✅ **VALID**: HEAD=VA, TAIL=VA (大便, 小便) - 最可靠标志
- ✅ **VALID**: HEAD=VV, TAIL=VV (军训, 暂停)
- ✅ **VALID**: HEAD=VV|AD, TAIL=NN (体检, 同学)
- ❌ **REJECT**: HEAD=NN, TAIL=NN 且为整词（小便宜/NN - 非离合词）
- ⚠️ Different from Verb-Object: VA标签是区分关键，Verb-Object不应有VA

### 2.3 Pseudo V-O (伪动宾式, 3.8%)

**HEAD POS Distribution (6 cases):**
- VV (verb): 4 (66.7%)
- NN (noun): 1 (16.7%, 整词"学习/NN")
- N/A: 1 (16.7%, 未分离)

**TAIL POS Distribution:**
- NN (noun): 5 (83.3%)
- N/A: 1 (16.7%)

**Examples:**
- **VV→NN**: 提醒(提/VV 醒/NN), 出恭(出/VV 恭/NN), 将军(将/VV 军/NN), 学习(学/VV 习/NN)
- **NN→NN**: 学习/NN (整词未分离)

**Validation Rules for Pseudo V-O:**
- ✅ **VALID**: HEAD=VV, TAIL=NN (主要模式)
- ⚠️ Similar to Verb-Object but less productive
- Note: 形式上与Verb-Object相同(VV→NN)，但语义不同

### 2.4 SimplexWord (单纯词, 1.9%)

**HEAD POS Distribution (3 cases):**
- VV (verb): 3 (100%)

**TAIL POS Distribution:**
- NN (noun): 2 (66.7%)
- VV (verb): 1 (33.3%, 整词"滑稽/VV")

**Examples:**
- **VV→NN**: 慷慨(慷/VV 慨/NN), 幽默(幽/VV 默/NN)
- **VV→VV**: 滑稽(滑天下之大稽/VV, 整词)

**Validation Rules for SimplexWord:**
- ✅ **VALID**: HEAD=VV, TAIL=NN|VV
- Note: 非真正离合词，属于成语或外来词临时拆分

---

## **Summary: HEAD/TAIL POS by Type**

| Liheci Type | HEAD POS (Most Common) | TAIL POS (Most Common) | Key Distinguisher |
|-------------|------------------------|------------------------|-------------------|
| **Verb-Object** | VV (97%) | NN (77%) / VV (20%) | HEAD=VV, TAIL≠AD/P/CS/CC |
| **Modifier-Head** | NN/VV/VA (mixed) | NN/VA/VV (mixed) | **VA标签出现** |
| **Pseudo V-O** | VV (67%) | NN (83%) | 与Verb-Object类似但数量少 |
| **SimplexWord** | VV (100%) | NN (67%) / VV (33%) | 特殊成语/外来词拆分 |

## 3. Insertion POS Patterns (Top 16)

| Rank | POS Tag | Count | Percentage | Meaning | Examples |
|------|---------|-------|------------|---------|----------|
| 1 | **AS** | 94 | 29.9% | Aspect (了/过/着) | 睡**了**觉, 走**着**路 |
| 2 | **CD** | 49 | 15.6% | Cardinal number | 睡了**一**个好觉 |
| 3 | **M** | 28 | 8.9% | Measure word | 睡了一**个**好觉 |
| 4 | **AD** | 20 | 6.4% | Adverb | 开**一下**门 |
| 5 | **PN** | 12 | 3.8% | Pronoun | 生**他**的气 |
| 6 | **DEG** | 10 | 3.2% | Genitive 的 | 生他**的**气 |
| 7 | VV | 9 | 2.9% | Verb | 起**不了**床 |
| 8 | JJ | 8 | 2.5% | Adjective | 睡了一个**好**觉 |
| 9 | NN | 8 | 2.5% | Noun | 写了**一手**好字 |
| 10 | DEC | 4 | 1.3% | Modification 的 | 做了一顿丰盛**的**晚饭 |
| 11 | NT | 4 | 1.3% | Temporal noun | 同**过三年**学 |
| 12 | DT | 4 | 1.3% | Determiner | 站**这**一班岗 |

## 4. Mapping to My Insertion Types

### 4.1 ASPECT_QUANT (Aspect + Quantifier)
**POS Pattern:** `AS + CD + M` (+ optional modifiers)
- Example: 睡**了/AS 一/CD 个/M 好/JJ**觉
- Example: 做**了/AS 一/CD 顿/M 丰盛/JJ 的/DEG**晚饭

### 4.2 QUANTIFIER (Number + Classifier only)
**POS Pattern:** `CD + M` (no AS)
- Example: 站**这/DT 一/CD 班/M**岗
- Example: 洗**个/M**热水澡

### 4.3 ASPECT (Aspect marker only)
**POS Pattern:** `AS` alone
- Example: 走**着/AS**路
- Example: 关**了/AS**灯

### 4.4 PRONOUN_DE (Pronoun + 的)
**POS Pattern:** `PN + DEG`
- Example: 生**他/PN 的/DEG**气
- Example: 捣**他/PN 的/DEG**乱

### 4.5 PRONOUN (Pronoun only)
**POS Pattern:** `PN` (without DEG)
- Rare in data, but possible

### 4.6 MODIFIER_DE (Modifier + 的)
**POS Pattern:** `(JJ|VA|AD) + DEG`
- Example: 做**了一顿丰盛/JJ 的/DEG**晚饭

### 4.7 MODIFIER (Modifier only)
**POS Pattern:** `JJ|VA|AD` (without DEG)
- Example: 睡了一个**好/JJ**觉
- Example: 开**一下/AD**门

### 4.8 RESULTATIVE (Result complement)
**POS Pattern:** Complex VV patterns
- Example: 起**不/AD 了/VV**床
- Example: 吃**完/VV**饭

### 4.9 EXT_PP (External preposition phrase)
**POS Pattern:** `P + (PN|NN)` **BEFORE HEAD**
- Example: **给/P 人家/PN** 道一个歉
- Example: **向/P 主人/NN** 道了一声谢
- **CRITICAL**: This should appear BEFORE HEAD, not in insertion!

## 5. False Positive Detection Rules

### 5.1 "大便" False Positive (Line 264 from previous analysis)
**Sentence:** 父亲18岁**大**的时候**便**去广东打工了
**Problem:** Matched "大便" but it's not a liheci

**POS Analysis:**
- HEAD: 大/VA (adjective-verb, "big/when X is big")
- INSERTION: 的/DEG 时候/NN (grammatical structure)
- TAIL: 便/AD (adverb, "then/immediately")

**Detection Rules:**
1. ❌ **TAIL POS is AD** (adverb) → NOT a valid Verb-Object liheci
   - Valid Verb-Object TAIL should be NN (77%) or VV (20%)
   - AD as TAIL indicates it's a sentence conjunction, not object

2. ❌ **HEAD is VA + TAIL is AD** → Impossible for 大便 Modifier-Head type
   - Real "大便" should be: HEAD=VA, TAIL=VA (both adjective-verbs)
   - Or in proper usage: 大/VA <HEAD> [X] <TAIL> 便/VA

3. ❌ **Insertion contains "的时候"** → Temporal clause, not liheci insertion
   - Real liheci insertions: AS, CD+M, PN+DEG, JJ, etc.
   - "的时候" is a temporal marker, grammatically wrong for 大便

**Rule Summary:** Reject if TAIL POS ∈ {AD, P, CS, CC} (functional words, not nouns/verbs)

### 5.2 PP_POS Errors (Lines 269-276)
**Examples:**
- 见**跟他/P+PN**面
- 吵**跟她/P+PN**架
- 打**跟同学/P+NN**架
- 道**向她/P+PN**歉

**Problem:** Preposition phrases (P+PN/NN) inside insertion span

**Detection Rules:**
1. ❌ **P (preposition) inside insertion** for words in `NO_PP_INSERT_WORDS`
   - NO_PP_INSERT_WORDS = {道歉, 道谢, 拜年, 见面, 吵架, 打架, 打仗, 开玩笑}
   - These words CANNOT have PP in insertion
   - PP should be BEFORE HEAD (external): **向/P 她/PN** 道[一个]歉 ✅

2. ✅ **Valid pattern:** PP appears before HEAD
   - Check tokens BEFORE <HEAD> marker for P tag
   - If found, classify as EXT_PP (external PP), not error

## 6. Pronoun + "的" (DEG) Validation Rules

### 6.1 Statistical Overview (159 Verb-Object cases analyzed)

| Pattern | Count | Percentage | Description |
|---------|-------|------------|-------------|
| **NO_PN + NO_DEG** | 124 | 87.9% | 最常见：无代词，无"的" (睡**了一个**觉) |
| **NO_PN + DEG** | 7 | 5.0% | 形容词性修饰语+"的" (做**了一顿丰盛的**晚饭) |
| **PN + DEG** | 6 | 4.3% | 代词所有格 (生**他的**气) |
| **PN + NO_DEG** | 4 | 2.8% | 直接宾语 (帮**了我一个**忙) |

### 6.2 Lexicon-Based Pronoun + DEG Rules

#### 6.2.1 PRON_POSS_REQUIRED (必须有"的")
**词表:** 捣乱, 吃醋, 领情, 革命, 造反, 丢脸
**规则:** 当插入语包含代词(PN)时，**必须**后接DEG(的)
**POS Pattern:** `PN + DEG` (required)
**例句:**
- 捣**他/PN 的/DEG**乱 ✅
- 吃**谁/PN 的/DEG**醋 ✅
- 革**自己/PN 的/DEG**命 ✅

**验证逻辑:**
```python
if 'PN' in insertion_pos_sequence and not has_DEG:
    confidence = 0.0  # 严格拒绝
    error_type = 'MISSING_REQUIRED_DE'
```

**数据符合率:** 80% (4/5有DEG, 1例"造反"为SP标注疑似误差)

#### 6.2.2 PRON_POSS_PREFERRED (更自然有"的")
**词表:** 生气
**规则:** 代词后**建议**加DEG，但省略也可接受
**POS Pattern:** `PN + DEG` (preferred)
**例句:**
- 生**他/PN 的/DEG**气 ✅ (更自然)
- 生**他**气 ⚠️ (可接受但不够自然)

**验证逻辑:**
```python
if 'PN' in insertion_pos_sequence and not has_DEG:
    confidence *= 0.8  # 轻微惩罚
    note = 'PREFERRED_DE_MISSING'
```

**数据符合率:** 100% (1/1有DEG)

#### 6.2.3 PRON_OBJ_OK (直接宾语，不需要"的")
**词表:** 帮忙, 告状, 将军
**规则:** 代词作为直接宾语，**不需要**DEG
**POS Pattern:** `PN` (without DEG, direct object)
**例句:**
- 帮**了/AS 我/PN 一个/CD**忙 ✅
- 告**了/AS 你/PN 一/CD**状 ✅
- 将**了/AS 他/PN 一/CD**军 ✅

**验证逻辑:**
```python
# DEG可有可无，不做惩罚
pass
```

**数据符合率:** 100% (3/3无DEG)

#### 6.2.4 NO_DIRECT_NP (不允许直接代词插入)
**词表:** 见面, 吵架, 打架, 打仗, 道歉, 道谢, 拜年
**规则:** 这些词**不允许**代词直接插入离合词中间，应使用外置介词短语
**正确形式:** 介词短语在HEAD前
- **跟/P 他/PN** 见[一]面 ✅
- **向/P 她/PN** 道[一个]歉 ✅

**错误形式:** 代词插在中间
- 见**他/PN**面 ❌
- 道**她/PN**歉 ❌

**验证逻辑:**
```python
if 'PN' in insertion_pos_sequence:
    confidence = 0.0
    error_type = 'INVALID_PRONOUN_INSERTION'
```

### 6.3 Non-Pronoun DEG Patterns (形容词性修饰语)

**Pattern:** `(JJ|VA|VV) + (DEG|DEC)`
**功能:** 修饰名词性宾语，非所有格
**例句:**
- 做**了一顿/CD+M 丰盛/JJ 的/DEG**晚饭 (修饰"晚饭")
- 谈**了一场/CD+M 轰轰烈烈/VV 的/DEC**恋爱 (修饰"恋爱")
- 跳**了一支/CD+M 优美/VA 的/DEC**舞 (修饰"舞")
- 受**了很/AD 重/VA 的/DEC**伤 (修饰"伤")

**说明:** 这些DEG/DEC是**修饰语标记**，与代词所有格无关，属于正常语法结构，**不应扣分**

### 6.4 Summary: 验证规则优先级

| Lexicon Rule | PN Present | DEG Present | Action |
|--------------|------------|-------------|--------|
| PRON_POSS_REQUIRED | ✓ | ✗ | **Reject** (confidence=0.0) |
| PRON_POSS_REQUIRED | ✓ | ✓ | Accept (confidence=1.0) |
| PRON_POSS_PREFERRED | ✓ | ✗ | **Penalize** (confidence×0.8) |
| PRON_POSS_PREFERRED | ✓ | ✓ | Accept (confidence=1.0) |
| PRON_OBJ_OK | ✓ | ✗/✓ | Accept (no constraint) |
| NO_DIRECT_NP | ✓ | any | **Reject** (confidence=0.0) |
| NONE (no rule) | ✓ | any | Accept (no validation) |
| any | ✗ | ✓ (JJ/VA+DEG) | Accept (modifier, not possessive) |

**注意:** 
1. "无DEG例句"不代表"禁止DEG"，只是当前数据未覆盖
2. 大部分离合词(87.9%)无代词插入，因此无DEG验证需求
3. 形容词性修饰语+DEG（如"丰盛的"）与代词所有格+DEG（如"他的"）是**不同语法功能**

## 7. Proposed Validation Pipeline

### Stage 3 Refactoring: POS-Aware Validation

**Input:** Sentence with HanLP POS tags
**Example:** 父亲/NN 18/CD 岁/M 大/VA 的/DEG 时候/NN 便/AD 去/VV...

**Step 1: Pre-validation (Before HFST lookup)**
1. Extract HEAD and TAIL from HFST output
2. Get POS tags for HEAD and TAIL from HanLP annotation
3. **Validate HEAD/TAIL POS by liheci type:**
   - If `type=Verb-Object`: Check HEAD≈VV (97%), TAIL≈NN (77%) or TAIL≈VV (20%)
   - If `type=Modifier-Head`: Check HEAD∈{VA,VV,AD}, TAIL∈{VA,VV,NN}
   - **REJECT if mismatch**: e.g., "大便" with HEAD=VA, TAIL=AD → confidence = 0.0

**Step 2: Insertion POS Extraction**
1. Extract POS tags for tokens between <HEAD> and <TAIL>
2. Build POS sequence: `AS CD M JJ`
3. **Check for invalid patterns:**
   - If contains `P` (preposition) and lemma ∈ NO_PP_INSERT_WORDS → confidence = 0.0
   - If TAIL POS ∈ {AD, P, CS, CC} → confidence = 0.0 (functional words)

**Step 3: DE Classification Check**
1. Check if `DEG` or `DEC` exists in insertion POS sequence
2. Apply rules:
   - `lemma ∈ REQUIRE_DE and no DEG` → confidence = 0.0
   - `lemma ∈ FORBIDDEN_DE and has DEG` → confidence = 0.0
   - `lemma ∈ OPTIONAL_DE` → no constraint

**Step 4: External PP Detection**
1. Extract tokens BEFORE <HEAD> marker (last 10 tokens)
2. Check for `P + (PN|NN)` pattern
3. If found → classify as EXT_PP (confidence = 0.8)
4. Ensure this PP is NOT counted as insertion error

**Step 5: POS-Based Insertion Classification**
Use POS patterns instead of character matching:
- `AS + CD + M` → ASPECT_QUANT
- `CD + M` (no AS) → QUANTIFIER
- `AS` alone → ASPECT
- `PN + DEG` → PRONOUN_DE
- `PN` (no DEG) → PRONOUN
- `(JJ|VA|AD) + DEG` → MODIFIER_DE
- `JJ|VA|AD` (no DEG) → MODIFIER
- Complex VV patterns → RESULTATIVE
- Empty → EMPTY
- P-initial (before HEAD) → EXT_PP

## 8. Implementation Plan

### 8.1 New Script: `07.hanlp_pos_integration.py`

**Functions:**
```python
def load_hanlp_annotations(tsv_path):
    """Load sentence → POS annotation mapping"""
    
def extract_pos_tags(pos_sentence, start_idx, end_idx):
    """Extract POS sequence for token range"""
    
def validate_head_tail_pos(head_pos, tail_pos, liheci_type):
    """Return validation result and confidence adjustment"""
    # Verb-Object: VV→NN (best), VV→VV (ok), VA→VA (wrong)
    # Modifier-Head: VA→VA (ok), VV→VV (ok)
    
def classify_by_pos_pattern(pos_sequence):
    """Classify insertion type by POS pattern"""
    
def check_pp_position(pos_sentence, head_idx, tail_idx):
    """Check if P appears before HEAD (valid) or inside insertion (invalid)"""
    
def validate_de_constraints(lemma, pos_sequence):
    """Check REQUIRE_DE, FORBIDDEN_DE, OPTIONAL_DE"""
```

### 8.2 Modified: `06.stage3_insertion_analysis.py`

**Changes:**
1. Add HanLP POS integration
2. Replace character-based classification with POS-based classification
3. Add HEAD/TAIL POS validation
4. Enhance error detection with POS rules
5. Change PP_POS from penalty (×0.2) to rejection (=0.0)

### 8.3 Word Lists to Define

```python
# Already defined
REQUIRE_DE_WORDS = {'捣乱', '丢脸', '造反', '革命'}
NO_PP_INSERT_WORDS = {'道歉', '道谢', '拜年', '见面', '吵架', '打架', '打仗', '开玩笑'}

# Need to define
FORBIDDEN_DE_WORDS = {
    # Aspectual liheci that never take 的
    '睡觉', '吃饭', '洗澡', '刷牙', '理发', ...
}

OPTIONAL_DE_WORDS = {
    # Most V-O liheci that can optionally have 的
    # (Basically any liheci not in REQUIRE_DE or FORBIDDEN_DE)
}

# Blacklist for false positives
FALSE_POSITIVE_PATTERNS = {
    ('大', 'VA', '便', 'AD'),  # 大/VA ... 便/AD (not 大便)
    ('小', 'VA', '便', 'AD'),  # Similar pattern
    # Add more as discovered
}
```

## 9. Expected Improvements

### 9.1 Accuracy Gains
- **False positive reduction**: Detect "大便" mismatches (TAIL=AD instead of VA)
- **PP error rejection**: Change from 0.2 penalty to 0.0 rejection
- **DE constraint enforcement**: Strict validation instead of soft penalties

### 9.2 Validation Coverage
- **Type-specific rules**: Verb-Object vs Modifier-Head different validation
- **POS-based classification**: More reliable than character matching
- **Position-aware PP detection**: Distinguish internal PP (error) from external PP (valid)

### 9.3 Output Quality
- New TSV columns: `head_pos`, `tail_pos`, `insertion_pos_sequence`, `pos_validation_status`
- Error types: Add `POS_MISMATCH`, `TAIL_INVALID`, `PP_POSITION_ERROR`
- Confidence more accurate: Based on multiple POS constraints

## 10. Next Steps

1. ✅ **Analyze HanLP POS patterns** (DONE - this document)
2. 🔲 Define FORBIDDEN_DE_WORDS list (need user input)
3. 🔲 Create `07.hanlp_pos_integration.py` with helper functions
4. 🔲 Modify `06.stage3_insertion_analysis.py` to use POS validation
5. 🔲 Test on problematic cases (line 264, lines 269-276)
6. 🔲 Run on full 206 rows and compare with previous output
7. 🔲 Update documentation (README.md, pipeline.md)
8. 🔲 Git commit and push

---

**Key Insight:** The HanLP POS tags provide structural validation that character-based rules cannot achieve. By checking HEAD/TAIL POS conformance and insertion POS patterns, we can reject false positives like "大便" (VA→AD instead of VA→VA) and properly validate grammatical constraints.
