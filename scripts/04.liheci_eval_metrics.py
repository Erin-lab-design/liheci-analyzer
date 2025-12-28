#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Liheci Evaluation Script

从：
  - test_sentences.txt
  - liheci_hfst_outputs.tsv
计算 HFST 对 “target stem 是否在句中出现” 的：
  - TP / FP / FN / TN
  - accuracy / precision / recall / F1
"""

import csv

TEST_FILE = "test_sentences.txt"
TSV_FILE = "liheci_hfst_outputs.tsv"


def load_gold_cases(test_file):
    """
    读取 test_sentences.txt
    返回:
        gold_by_id: {case_id: {"stem": ..., "label": True/False, "sentence": ...}}
    case_id 按出现顺序从 1 开始编号（和 exporter 一样）
    """
    gold_by_id = {}
    case_id = 0

    with open(test_file, "r", encoding="utf-8") as fin:
        for raw_line in fin:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            parts = [p.strip() for p in line.split("|")]
            if len(parts) != 3:
                # 这一行格式不对，跳过
                continue

            stem, sentence, flag = parts
            case_id += 1
            gold_label = (flag.lower() == "true")

            gold_by_id[case_id] = {
                "stem": stem,
                "label": gold_label,
                "sentence": sentence,
            }

    return gold_by_id


def load_system_detections(tsv_file):
    """
    读取 liheci_hfst_outputs.tsv
    返回:
        detected_lemmas_by_case: {case_id: set([lemma1, lemma2, ...])}
    注意：只对有 HFST 命中的 case_id 有记录；
         没命中的 case_id 不会出现在这个 dict 里。
    """
    detected_lemmas_by_case = {}

    with open(tsv_file, "r", encoding="utf-8") as fin:
        reader = csv.reader(fin, delimiter="\t")
        header = next(reader, None)  # 跳过 header

        for row in reader:
            if not row or len(row) < 9:
                continue

            case_id_str, gold_stem, gold_label_str, sentence, lemma, type_tag, shape, is_redup_str, raw = row
            try:
                case_id = int(case_id_str)
            except ValueError:
                continue

            detected_lemmas_by_case.setdefault(case_id, set()).add(lemma)

    return detected_lemmas_by_case


def evaluate(gold_by_id, detected_lemmas_by_case):
    """
    根据 gold_by_id 和 detected_lemmas_by_case 计算 TP/FP/FN/TN
    规则：
        predicted_positive = (gold_stem in detected_lemmas_for_case)
    """
    TP = FP = FN = TN = 0

    for case_id, gold in gold_by_id.items():
        gold_stem = gold["stem"]
        gold_label = gold["label"]

        detected_lemmas = detected_lemmas_by_case.get(case_id, set())

        predicted_positive = (gold_stem in detected_lemmas)

        if gold_label:
            if predicted_positive:
                TP += 1
            else:
                FN += 1
        else:
            if predicted_positive:
                FP += 1
            else:
                TN += 1

    return TP, FP, FN, TN


def compute_metrics(TP, FP, FN, TN):
    N = TP + FP + FN + TN
    acc = (TP + TN) / N if N > 0 else 0.0

    prec = TP / (TP + FP) if (TP + FP) > 0 else 0.0
    rec = TP / (TP + FN) if (TP + FN) > 0 else 0.0
    f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0

    return {
        "N": N,
        "accuracy": acc,
        "precision": prec,
        "recall": rec,
        "f1": f1,
    }


def main():
    gold_by_id = load_gold_cases(TEST_FILE)
    detected_lemmas_by_case = load_system_detections(TSV_FILE)

    TP, FP, FN, TN = evaluate(gold_by_id, detected_lemmas_by_case)
    metrics = compute_metrics(TP, FP, FN, TN)

    print("=== Confusion Matrix (per case, target stem) ===")
    print(f"TP = {TP}")
    print(f"FP = {FP}")
    print(f"FN = {FN}")
    print(f"TN = {TN}")
    print()

    print("=== Metrics ===")
    print(f"N         = {metrics['N']}")
    print(f"Accuracy  = {metrics['accuracy']:.4f}")
    print(f"Precision = {metrics['precision']:.4f}")
    print(f"Recall    = {metrics['recall']:.4f}")
    print(f"F1        = {metrics['f1']:.4f}")


if __name__ == "__main__":
    main()
