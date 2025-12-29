Input Sentence
    ↓
[Stage 1] HFST Basic Recognition (WHOLE/SPLIT/REDUP)
    └─ liheci_split.analyser.hfst (all 131 lemmas)
        ├─ WHOLE: contiguous form (睡觉)
        ├─ SPLIT: inserted form (睡了觉, 睡个好觉)
        └─ REDUP: reduplication form (散散步, 散一散步)
    ↓
Candidate liheci list with basic patterns
    ↓
[Stage 2] HFST Insertion Type Recognition
    └─ insertion_classifier.hfst
        ├─ Aspect markers (了, 过, 着)
        ├─ Quantifier phrases (一个, 三次)
        ├─ Pronouns (我, 你, 他)
        ├─ Result complements (完, 好, 到)
        └─ "的" marker
    ↓
Candidates with insertion type annotations
    ↓
[Stage 3A] HFST Coarse-grained Filtering (Optional)
    ├─ Filter obvious transitivity errors
    ├─ Check required PP structures
    └─ Filter obvious pronoun errors
    ↓
Initially filtered candidates
    ↓
[Stage 3B] Python Fine-grained Validation
    ├─ Semantic-level transitivity check
    ├─ Context-dependent PP validation
    ├─ Semantic role judgment for pronoun insertion
    └─ Other complex rules
    ↓
Final Results