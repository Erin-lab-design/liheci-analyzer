import subprocess
import os

def run_debug():
    # 1. 动态获取绝对路径，确保在哪跑都能找到文件夹
    current_file_path = os.path.abspath(__file__)
    base_dir = os.path.dirname(current_file_path) # liheci_project 根目录
    fst_dir = os.path.join(base_dir, 'fst')
    
    # 文件名 (只用文件名，不用路径)
    xfst_file = 'middle_grammar.xfst'
    hfst_file = 'middle.hfst'
    
    # 完整路径用于检查文件是否存在
    hfst_abs_path = os.path.join(fst_dir, hfst_file)

    print(f"工作目录锁定为: {fst_dir}")

    # === 清理旧文件 ===
    if os.path.exists(hfst_abs_path):
        os.remove(hfst_abs_path)
        print(">>> 已清理旧的 middle.hfst，准备全新编译...")

    # === 开始编译 ===
    print(">>> 正在编译...")
    
    # 关键修正：命令里只写文件名
    cmd = [
        'hfst-xfst',
        '-e', f'source {xfst_file}',
        '-e', f'save stack {hfst_file}',
        '-e', 'quit'
    ]
    
    try:
        # 关键修正：cwd=fst_dir
        # 这相当于先在终端里执行了 `cd fst`，然后再执行命令
        result = subprocess.run(
            cmd,
            cwd=fst_dir,          # <--- 这里的魔法！
            capture_output=True,
            text=True
        )
        
        # 检查是否生成了文件
        if os.path.exists(hfst_abs_path) and os.path.getsize(hfst_abs_path) > 0:
            print(f"✅ 编译成功！文件大小: {os.path.getsize(hfst_abs_path)} bytes")
        else:
            print("❌ 编译失败！输出如下：")
            print(result.stdout)
            print(result.stderr)
            return # 编译失败就不要测试了

    except Exception as e:
        print(f"❌ 执行出错: {e}")
        return

    # === 冒烟测试 ===
    print("\n>>> 正在进行冒烟测试 (Test Input: '个@@')...")
    try:
        test_input = "个某某" # 对应：Cl + Mod + Mod
        
        process = subprocess.Popen(
            ['hfst-lookup', '-q', hfst_file],
            cwd=fst_dir,          # <--- 测试时也要在 fst 目录下
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(input=test_input + "\n")
        
        if "+?" in stdout or "inf" in stdout or not stdout.strip():
            print(f"❌ 测试不通过。FST输出: {stdout.strip()}")
        else:
            print(f"✅ 测试通过！FST输出: {stdout.strip()}")
            print("\n🎉 现在你可以去运行 python3 src/main.py 了！")

    except Exception as e:
        print(f"❌ 测试出错: {e}")

if __name__ == "__main__":
    run_debug()