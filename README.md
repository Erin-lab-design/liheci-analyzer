# Liheci HFST Analyzer

**[English](README.md)** | [简体中文](README_ZH.md)

---

Chinese separable verb (离合词, liheci) analyzer using HFST (Helsinki Finite-State Technology).

## Introduction

This project uses Finite-State Transducer (FST) technology to recognize and analyze Chinese separable verbs (liheci). Liheci are a special class of words in Modern Chinese that allow insertion of other elements between their two morphemes:

- 睡觉 → 睡了一个好觉 (SPLIT: slept a good sleep)
- 散步 → 散散步 (REDUP: take a stroll)
- 见面 → 跟朋友见面 (with PP: meet with friends)

**Four-Stage HFST Pipeline**:
- **Stage 1**: Recognize WHOLE/SPLIT forms (all 131 lemmas)
- **Stage 2**: Validate REDUP reduplication forms (55 AAB lemmas)
- **Stage 3**: HFST character-level annotation + Python insertion type classification, confidence scoring (167 rows)
- **Stage 4**: HanLP POS validation, filter invalid POS/PP/DE errors (160 rows)

**Final Performance**: Precision 92.36%, Recall 97.32%, F1 94.77%

## Features

- ✅ **Stage 1**: Recognize **WHOLE** forms (contiguous): 睡觉
- ✅ **Stage 1**: Recognize **SPLIT** forms (with insertion): 睡了一觉
- ✅ **Stage 2**: Validate **REDUP** reduplication: 散散步 ✓ / *结结婚 ✗
- ✅ **Stage 3**: Character-level annotation + insertion type classification (167 rows, Precision 87.43%)
- ✅ **Stage 4**: HanLP POS validation, high-precision output (160 rows, Precision 92.36%, F1 94.77%)
- ✅ Multiple insertion types: aspect markers, quantifiers, pronouns, resultatives, modifiers
- ✅ Confidence scoring (0.0-1.0) based on annotation coverage
- ✅ Error detection: MISSING_DE, PP_POS, POS validation
- ✅ Sentence-level analysis with automatic liheci positioning
- ✅ Multi-stage filtering for high precision

## Project Structure

```
liheci-analyzer/
├── data/
│   ├── liheci_lexicon.csv        # Lexicon (131 liheci entries)
│   └── test_sentences.txt        # Test sentences (284 instances)
│
├── scripts/
│   ├── hfst_files/               # Compiled HFST files
│   │   ├── liheci_split.analyser.hfst       # [Stage 1] Analyser
│   │   ├── liheci_split.generator.hfst      # [Stage 1] Generator
│   │   ├── liheci_redup.analyser.hfst       # [Stage 2] Analyser
│   │   ├── liheci_redup.generator.hfst      # [Stage 2] Generator
│   │   ├── liheci_insertion_annotator.hfst  # [Stage 3] Annotator
│   │   └── *.xfst                           # XFST rule files
│   │
│   ├── 01.generate_liheci_split_xfst.py     # [Stage 1] Generate XFST
│   ├── 03.stage1_split_whole_recognition.py # [Stage 1] Run recognition
│   ├── 02.generate_liheci_redup_xfst.py     # [Stage 2] Generate XFST
│   ├── 04.stage2_redup_recognition.py       # [Stage 2] Validate REDUP
│   ├── 05.generate_insertion_context_xfst.py # [Stage 3] Generate annotator
│   ├── 06.stage3_insertion_analysis.py      # [Stage 3] Insertion analysis
│   └── 07.stage4_pos_validation.py          # [Stage 4] POS validation
│
├── outputs/
│   ├── liheci_hfst_outputs.tsv              # Stage 1+2 output (190 rows)
│   ├── liheci_insertion_analysis.tsv        # Stage 3 output (167 rows)
│   ├── liheci_pos_validated.tsv             # Stage 4 final output (160 rows)
│   ├── liheci_pos_rejected.tsv              # Stage 4 rejected (10 rows)
│   └── logs/
│
├── hfst-3.16.2/                             # HFST toolkit (Windows)
├── pipeline.md                               # Pipeline documentation
└── README.md                                 # This file (Chinese)
```

## Requirements

- Python 3.7+
- HFST toolkit (hfst-xfst, hfst-lookup)
- HanLP (for Stage 4)

## Installation

### 1. Install HFST

**macOS:**
```bash
brew install hfst
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt-get install hfst

# Or build from source
git clone https://github.com/hfst/hfst.git
cd hfst
./configure && make && sudo make install
```

**Windows:**
Pre-compiled binaries included in `hfst-3.16.2/` folder.

### 2. Clone Project

```bash
git clone https://github.com/Erin-lab-design/liheci-analyzer.git
cd liheci-analyzer
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

## Usage

### Run Full Pipeline (Recommended)

```bash
# Stage 1: Recognize WHOLE/SPLIT forms
python scripts/03.stage1_split_whole_recognition.py
# Output: outputs/liheci_hfst_outputs.tsv (301 rows)

# Stage 2: Validate REDUP
python scripts/04.stage2_redup_recognition.py
# Output: outputs/liheci_hfst_outputs.tsv (190 rows)

# Stage 3: Insertion analysis with confidence filtering
python scripts/06.stage3_insertion_analysis.py
# Output: outputs/liheci_insertion_analysis.tsv (167 rows)

# Stage 4: POS validation
python scripts/07.stage4_pos_validation.py
# Output: outputs/liheci_pos_validated.tsv (160 rows, Precision 92.36%)
```

### Command Line Testing

```bash
# Test WHOLE/SPLIT recognition
echo "我昨天睡了一个好觉" | hfst-lookup scripts/hfst_files/liheci_split.analyser.hfst

# Test REDUP recognition
echo "散散步" | hfst-lookup scripts/hfst_files/liheci_redup.analyser.hfst
```

## Output Format

### Stage 3 Output (`liheci_insertion_analysis.tsv`)

167 rows (confidence threshold ≥ 0.3), Precision 87.43%, Recall 97.99%, F1 92.41%:

| insertion | insertion_tagged | insertion_type | confidence_score |
|-----------|------------------|----------------|------------------|
| 了一个好 | 了:ASPECT+一:NUM+个:CLF+好:MOD | ASPECT_QUANT | 1.00 |
| 个热水 | 个:CLF | QUANTIFIER | 0.33 |
| 完 | 完:RES | RESULTATIVE | 1.00 |

**Insertion Types**: ASPECT_QUANT, ASPECT, QUANTIFIER, PRONOUN_DE, PRONOUN, MODIFIER_DE, MODIFIER, RESULTATIVE, EXT_PP, EMPTY, REDUP_SKIP, UNKNOWN

### Stage 4 Output (`liheci_pos_validated.tsv`)

160 rows (157 unique predictions), **Precision 92.36%, Recall 97.32%, F1 94.77%**:

- HanLP POS validation by liheci type
- **POS Rules**:
  - Verb-Object: HEAD=VV, TAIL=NN/NR/NT/VV/M/VA
  - Modifier-Head: HEAD=VV/VA/AD, TAIL=NN/NR/NT/VA/VV
- **TAIL Blacklist**: AD, P, CS, CC, DT, DEG, DEC, AS, SP
- Final: TP=145, FP=12, FN=4

## Limitations

1. **REDUP**: Only supports AAB pattern (散散步), not ABAB (调查调查)
2. **COINCIDENCE**: Character coincidence errors require semantic understanding
3. **Unidirectional**: Analysis only, no sentence generation
4. **Processing Speed**: Sequential HFST lookup, consider parallelization for large datasets

## References

- [pipeline.md](pipeline.md) - Detailed pipeline architecture
- [HFST - Helsinki Finite-State Technology](https://hfst.github.io/)
- [HanLP](https://github.com/hankcs/HanLP)

---
*Repository: [https://github.com/Erin-lab-design/liheci-analyzer](https://github.com/Erin-lab-design/liheci-analyzer)*
