import subprocess
import os
import sys

def run_debug():
    print("=== 1. 正在强制重新编译 FST... ===")
    fst_dir = os.path.join(os.getcwd(), 'fst')
    xfst_file = os.path.join(fst_dir, 'middle_grammar.xfst')
    hfst_file = os.path.join(fst_dir, 'middle.hfst')
    
    # 编译命令
    cmd = f'hfst-xfst -e "source {xfst_file}" -e "save stack {hfst_file}" -e "quit"'
    print(f"执行命令: {cmd}")
    
    ret = os.system(cmd)
    if ret != 0:
        print("❌ 编译失败！请检查终端报错。")
        return

    if not os.path.exists(hfst_file):
        print("❌ 编译看起来成功了，但 middle.hfst 文件不存在！")
        return
        
    print(f"✅ FST 编译成功！文件大小: {os.path.getsize(hfst_file)} bytes")
    
    print("\n=== 2. 正在进行冒烟测试 (Smoke Test) ===")
    # 模拟 '洗澡' 的中间部分: "个热水" -> 归一化后 -> "个@@"
    # "个" 在 FST_KEYWORDS 里，"热"和"水"不在，所以变成 @
    test_input = "个@@" 
    
    print(f"测试输入字符串: '{test_input}'")
    
    try:
        process = subprocess.Popen(
            ['hfst-lookup', '-q', hfst_file],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # 发送输入 (一定要加 \n)
        stdout, stderr = process.communicate(input=test_input + "\n")
        
        print(f"FST 输出结果:\n{stdout.strip()}")
        
        if "+?" in stdout or "inf" in stdout or not stdout.strip():
            print("❌ 测试失败: FST 拒绝了这个输入。")
            print("可能原因: 规则里没有涵盖 'Cl + Mod + Mod' 的结构。")
        else:
            print("✅ 测试通过: FST 接受了这个输入！")
            print("现在你可以去跑 main.py 了。")
            
    except Exception as e:
        print(f"❌ 调用 hfst-lookup 出错: {e}")

if __name__ == "__main__":
    run_debug()