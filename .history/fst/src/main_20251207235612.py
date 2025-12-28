import os
import sys
# 导入你的检测逻辑
from liheci_detector import check_liheci_smart

def run_test_suite():
    # 1. 设置路径
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    data_path = os.path.join(base_dir, 'data', 'test_sentences.txt')
    hfst_path = os.path.join(base_dir, 'fst', 'middle.hfst')
    
    # 检查 FST 是否存在
    if not os.path.exists(hfst_path):
        print("错误：找不到 middle_field.hfst，请先编译 FST 脚本！")
        return

    print(f"Loading Test Data: {data_path}")
    print(f"Using FST Model: {hfst_path}")
    print("-" * 60)
    print(f"{'Target':<6} | {'Sentence':<30} | {'Exp':<5} | {'Act':<5} | {'Result'}")
    print("-" * 60)

    correct_count = 0
    total_count = 0

    # 2. 读取测试集
    with open(data_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'): continue
            
            try:
                # 解析格式: 睡觉 | 昨天晚上我睡了一个好觉。 | True
                parts = line.split('|')
                target_word = parts[0].strip()
                sentence = parts[1].strip()
                expected_str = parts[2].strip()
                expected = (expected_str == 'True')
                
                # 这一步需要把 target_word 拆成 A 和 B
                # 简单假设是双字词，或者是词典里查出来的。
                # 这里为了演示，默认前两个字是 A 和 B (你需要根据 lexicon.csv 完善这里)
                # 更好的方法是读取 lexicon.csv 建立映射
                # 临时方案：
                char_a = target_word[0]
                char_b = target_word[-1] # 取首尾，处理 "离了个大婚"
                if len(target_word) > 2 and target_word != "打仗": # 处理特殊情况
                     pass 

                # 3. 调用检测
                result, reason = check_liheci_smart(sentence, char_a, char_b, hfst_path)
                
                # 4. 统计与打印
                status = "PASS" if result == expected else "FAIL"
                if status == "PASS": correct_count += 1
                total_count += 1
                
                # 缩略打印
                short_sent = sentence[:20] + "..." if len(sentence) > 20 else sentence
                print(f"{target_word:<6} | {short_sent:<30} | {str(expected):<5} | {str(result):<5} | {status}")
                
                if status == "FAIL":
                    print(f"   >>> Debug: {reason}")

            except Exception as e:
                print(f"Error processing line: {line} -> {e}")

    # 5. 最终分数
    accuracy = (correct_count / total_count) * 100
    print("-" * 60)
    print(f"Total: {total_count}, Correct: {correct_count}, Accuracy: {accuracy:.2f}%")

if __name__ == "__main__":
    run_test_suite()