#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate XFST rules for insertion classification
Annotates each character with grammatical tags using replace rules
Input format: 昨天晚上我睡<HEAD>了一个好<TAIL>觉。
Output format: 了:ASPECT+一:NUM+个:CLF+好:MOD+
"""

import subprocess
from pathlib import Path

# Output paths
BASE_DIR = Path(__file__).parent
HFST_FILES_DIR = BASE_DIR / 'hfst_files'
OUTPUT_XFST = HFST_FILES_DIR / 'liheci_insertion_annotator.xfst'
OUTPUT_HFST = HFST_FILES_DIR / 'liheci_insertion_annotator.hfst'
HFST_XFST = BASE_DIR.parent / 'hfst-3.16.2' / 'hfst' / 'bin' / 'hfst-xfst.exe'


def generate_xfst():
    """
    Generate XFST that annotates each character with its category
    Output format: 了:ASPECT+一:NUM+个:CLF+好:MOD+
    Python will extract and classify later
    """
    
    xfst_content = '''! Insertion Character Annotator
! Marks each character with its grammatical category
! Output format: 字符:标签+字符:标签

! === Annotation Rules ===
! Use replace to add tags after each recognized character

! Aspect markers
define MarkAsp 了 -> 了 %: A S P E C T %+ ,
               过 -> 过 %: A S P E C T %+ ,
               着 -> 着 %: A S P E C T %+ ;

! Numerals
define MarkNum 一 -> 一 %: N U M %+ ,
               二 -> 二 %: N U M %+ ,
               两 -> 两 %: N U M %+ ,
               三 -> 三 %: N U M %+ ,
               四 -> 四 %: N U M %+ ,
               五 -> 五 %: N U M %+ ,
               六 -> 六 %: N U M %+ ,
               七 -> 七 %: N U M %+ ,
               八 -> 八 %: N U M %+ ,
               九 -> 九 %: N U M %+ ,
               十 -> 十 %: N U M %+ ,
               百 -> 百 %: N U M %+ ,
               千 -> 千 %: N U M %+ ,
               万 -> 万 %: N U M %+ ,
               几 -> 几 %: N U M %+ ,
               半 -> 半 %: N U M %+ ;

! Classifiers
define MarkClf 个 -> 个 %: C L F %+ ,
               次 -> 次 %: C L F %+ ,
               天 -> 天 %: C L F %+ ,
               把 -> 把 %: C L F %+ ,
               场 -> 场 %: C L F %+ ,
               声 -> 声 %: C L F %+ ,
               手 -> 手 %: C L F %+ ,
               根 -> 根 %: C L F %+ ,
               支 -> 支 %: C L F %+ ,
               首 -> 首 %: C L F %+ ,
               趟 -> 趟 %: C L F %+ ,
               遍 -> 遍 %: C L F %+ ,
               下 -> 下 %: C L F %+ ,
               年 -> 年 %: C L F %+ ,
               月 -> 月 %: C L F %+ ,
               日 -> 日 %: C L F %+ ,
               周 -> 周 %: C L F %+ ,
               回 -> 回 %: C L F %+ ;

! Pronouns
define MarkPro 我 -> 我 %: P R O %+ ,
               你 -> 你 %: P R O %+ ,
               他 -> 他 %: P R O %+ ,
               她 -> 她 %: P R O %+ ,
               它 -> 它 %: P R O %+ ;

! 的
define MarkDe 的 -> 的 %: D E %+ ;

! Modifiers
define MarkMod 好 -> 好 %: M O D %+ ,
               大 -> 大 %: M O D %+ ,
               小 -> 小 %: M O D %+ ,
               重 -> 重 %: M O D %+ ,
               轻 -> 轻 %: M O D %+ ,
               长 -> 长 %: M O D %+ ,
               短 -> 短 %: M O D %+ ,
               高 -> 高 %: M O D %+ ,
               厚 -> 厚 %: M O D %+ ,
               很 -> 很 %: M O D %+ ,
               整 -> 整 %: M O D %+ ;

! Resultatives
define MarkRes 完 -> 完 %: R E S %+ ,
               到 -> 到 %: R E S %+ ;

! Prepositions
define MarkPrep 跟 -> 跟 %: P R E P %+ ,
                和 -> 和 %: P R E P %+ ,
                与 -> 与 %: P R E P %+ ,
                向 -> 向 %: P R E P %+ ,
                对 -> 对 %: P R E P %+ ,
                给 -> 给 %: P R E P %+ ,
                为 -> 为 %: P R E P %+ ,
                被 -> 被 %: P R E P %+ ,
                把 -> 把 %: P R E P %+ ;

! === Compose All Annotations ===
define Annotator [
  MarkAsp .o.
  MarkNum .o.
  MarkClf .o.
  MarkPro .o.
  MarkDe .o.
  MarkMod .o.
  MarkRes .o.
  MarkPrep
];

regex Annotator;

save stack liheci_insertion_annotator.hfst
quit
'''
    
    return xfst_content


def main():
    print("="*60)
    print("Generate Insertion Annotator XFST")
    print("="*60)
    
    # Generate XFST
    xfst_code = generate_xfst()
    
    # Save XFST file
    print(f"\nSaving XFST file: {OUTPUT_XFST}")
    with open(OUTPUT_XFST, 'w', encoding='utf-8') as f:
        f.write(xfst_code)
    
    # Compile with hfst-xfst
    print(f"\nCompiling XFST → HFST...")
    result = subprocess.run(
        [str(HFST_XFST), '-F', str(OUTPUT_XFST)],
        cwd=str(HFST_FILES_DIR),
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"✗ Compilation failed!")
        print(f"STDERR:\n{result.stderr}")
        return
    
    print(f"✓ Successfully compiled: {OUTPUT_HFST}")
    print(f"\nSTDOUT:\n{result.stdout}")


if __name__ == '__main__':
    main()
