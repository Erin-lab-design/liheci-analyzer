1. Introduction

The accurate identification of Chinese separable verbs (离合词, liheci) remains a significant challenge for current part-of-speech (POS) taggers and word segmentation systems. Existing tools, such as HanLP and other mainstream Chinese NLP libraries, often fail to recognize the complex and flexible structures of liheci, leading to frequent errors in both automatic processing and language learning applications.

This issue is particularly pronounced for non-native learners of Chinese, who commonly struggle with the correct usage of separable verbs. Classic problems include whether to insert the possessive marker “的” after a pronoun within the inserted phrase, or whether a prepositional phrase can serve as a valid insertion. These subtle grammatical rules are rarely handled well by existing systems, resulting in confusion and persistent mistakes among learners.

Motivated by these challenges, this project aims to develop a robust, high-precision pipeline for the automatic recognition and analysis of Chinese separable verbs in natural text. By formalizing and implementing detailed recognition rules, the system not only improves the accuracy of liheci identification for computational applications, but also provides a valuable resource for Chinese language learners and educators. The insights gained from this project have also deepened my own understanding of the structural and functional properties of separable verbs, and I hope that the resulting tools and analyses can contribute to the improvement of existing NLP libraries and the broader field of Chinese language processing.

2. Background: Liheci in Chinese and Project Dataset
   Chinese separable verbs (liheci) are a unique lexical phenomenon, with over 2,500 entries listed in the authoritative Modern Chinese Dictionary and as many as 4,066 identified by scholars such as Yang Qinghui (1995), of which 1,738 are considered high-frequency. Many liheci are essential for learners of Chinese as a second language, including common verbs like “见面” (to meet), “散步” (to take a walk), and “吃饭” (to eat a meal).

Liheci are characterized by their dual nature: when contiguous, they function as a single word (e.g., “洗澡” to bathe), but when separated, they form a phrase (e.g., “洗一个澡” to take a bath). Despite their syntactic flexibility, liheci have a unified lexical meaning. Their hallmark is the ability to insert quantifiers, aspect markers, pronouns, or other modifiers between the head and tail components (e.g., “鼓掌” → “鼓了鼓掌”).

The most common type of liheci is the Verb-Object (VO) structure, but other types such as Modifier-Head and Simplex Words (often idioms or set phrases) also exist, though they are much less frequent and harder to collect systematically.

For this project, I compiled a dataset of 131 liheci, the majority of which are Verb-Object type or pseudo V-O type, reflecting the natural distribution of liheci in modern Chinese. The dataset also includes a small number of Modifier-Head and Simplex Word types, but these are rare and often idiomatic, making comprehensive collection difficult. Nevertheless, the current dataset is sufficient to capture the main structural and insertional patterns of liheci (head, tail, insertion), and provides a solid empirical basis for rule development and system evaluation.

2. Project Description

2.1 Overall Architecture&#x20;

The project is organized as a multi-stage pipeline, each stage designed to address a specific linguistic or technical challenge in the automatic recognition of Chinese separable verbs (liheci). The stages are:

Data Preparation: Curating a high-quality lexicon and annotated test set. FST Construction and Recognition: Using HFST/XFST to recognize both standard and reduplicated liheci forms. Insertion Component Analysis: Character-level annotation and classification of inserted elements. Confidence Scoring and Filtering: Quantitative filtering based on insertion analysis. POS-Based Validation: Further filtering using HanLP POS tagging and custom linguistic rules. Evaluation: Automated scoring and error analysis.&#x20;

2.2 Data Sources and Preprocessing Lexicon&#x20;

The core lexicon contains 131 liheci, mostly Verb-Object (VO) type, with a few Modifier-Head and Simplex Word types. Each entry includes head, tail, type, pinyin, English definition, and detailed insertion/PP/pronoun rules. Test Sentences: The test set covers a wide range of liheci usage, including positive and negative examples, and is annotated for gold standard evaluation. Error Types: The test set explicitly defines various error types (e.g., character coincidence, missing “的”, PP in wrong position, invalid reduplication, cross-constituent, reversed order, missing head/tail) to ensure robust evaluation and to avoid false positives due to mere character overlap.&#x20;

2.3 FST Construction and Recognition Scripted Generation

Python scripts automatically generate XFST rules from the lexicon, ensuring consistency and scalability. Separation of Standard and Reduplication Forms: Standard liheci (head-tail) and AAB/reduplication forms are recognized using separate FSTs. This design avoids combinatorial explosion in the FST state space, which would occur if all forms were handled in a single FST. Technical Rationale: The separation is necessary because many liheci allow A(一/了)AB forms, and combining all patterns in one FST would make compilation and recognition infeasible.&#x20;

2.4 Insertion Component Analysis Character-Level Annotation&#x20;

A dedicated HFST annotator marks each character in the insertion span with a fine-grained grammatical tag (e.g., ASPECT, NUM, CLF, MOD, PRO, DE, etc.), based on a linguistically motivated inventory. Insertion Type Classification: Insertions are classified into types (e.g., ASPECT_QUANT, QUANTIFIER, PRONOUN_DE, MODIFIER, RESULTATIVE, EXT_PP, etc.) according to their tag sequence. Special Rules: The system encodes special rules for pronoun insertion (e.g., some liheci allow direct pronoun insertion, others require “的” after a pronoun), and for the position of prepositional phrases (PPs). For example, some liheci only allow PPs before the head, not inside the split.&#x20;

2.5 Confidence Scoring and Filtering Motivation

Because Chinese is written without word boundaries, and character sequences can coincidentally match head and tail components, it is crucial to distinguish true liheci from accidental matches. Confidence Calculation: The confidence score is defined as the proportion of insertion characters that are recognized as valid types. For example, if all characters in the insertion are tagged as valid, confidence is 1.0. Thresholding: A relatively low threshold (default 0.3) is used to filter candidates, balancing recall and precision. This is based on empirical analysis and evaluation (see Stage 3 results). Technical Note: This approach is both simple and effective, but not absolute—hence the need for further validation in later stages.&#x20;

2.6 POS-Based Validation (Stage 4)&#x20;

Why Not Use HanLP in stage 3: HanLP and other POS taggers often segment or tag insertion elements in ways that do not align with the linguistically motivated categories used here. Their tagsets (e.g., VV, NN) are too coarse for insertion analysis, and integrating them at the FST level would be computationally infeasible.&#x20;

Instead, HanLP POS tagging is used after FST-based recognition, to validate the POS patterns of the head and tail. The system applies type-specific rules for acceptable head/tail POS combinations, further reducing false positives from character coincidence.&#x20;

2.7 Evaluation and Error Analysis Automated Evaluation: Scripts (e.g., evaluate_by06.py, evaluate_by07.py) compare system output to the gold standard, compute precision, recall, F1, and analyze error types. Results: The pipeline achieves high precision and recall, with average confidence around 0.9 after filtering. Error analysis shows that most remaining errors are due to subtle linguistic ambiguities.&#x20;

2.8 Attachment and File Overview

01.generate_liheci_split_xfst.py: Generates XFST rules for standard liheci recognition. 02.generate_liheci_redup_xfst.py: Generates XFST rules for reduplication (AAB) forms. 03.stage1_split_whole_recognition.py: Runs Stage 1 recognition using the compiled FSTs. 04.stage2_redup_recognition.py: Validates reduplication forms.&#x20;

05.generate_insertion_context_xfst.py: Generates the insertion annotator FST.&#x20;

06.stage3_insertion_analysis.py: Performs insertion analysis, type classification, and confidence scoring. 07.stage4_pos_validation.py: Applies POS-based validation rules.&#x20;

scripts/evaluate_by06.py, evaluate_by07.py: Automated evaluation scripts.&#x20;

scripts/hfst_files/: Contains all compiled FSTs and annotators.&#x20;

liheci_lexicon.csv: Main lexicon with detailed linguistic features.&#x20;


test_sentences.txt: Annotated test set with gold labels and error types. outputs/: Contains all intermediate and final results, as well as evaluation reports.

3. Testing and Evaluation
   说明你如何对系统进行测试（如：用人工标注的测试集，自动评测脚本evaluate_by06.py、evaluate_by07.py）。
   介绍评测指标（Precision, Recall, F1, Confusion Matrix等）。
   简要描述测试流程（如：每个阶段输出的文件、如何对比gold标准、如何统计错误类型）。

4. Results and Discussion
   总结主要实验结果（可引用outputs/liheci_evaluation_report_by06.txt和by07.txt中的数据）。
   对比不同阶段（如Stage 3和Stage 4）系统性能的提升。
   讨论主要错误类型（如COINCIDENCE、PP/DE、POS错误等），分析系统的优缺点和局限性。
   讨论置信度过滤、POS验证等设计对最终结果的影响。
   可以简要展望未来改进方向（如：更复杂的句法分析、更大规模的测试集等）。

5. Attachments
   列出所有相关代码（scripts/下的py脚本、xfst文件等），并简要说明每个文件的作用。
   列出主要数据文件（如lexicon、测试集、输出结果），说明其用途。
   可以附上部分关键输出（如典型的分析结果、错误分析表等）。

