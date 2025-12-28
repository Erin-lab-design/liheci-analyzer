import subprocess
import os

# ================= 配置区域 =================
# 这里填你刚才告诉我的准确路径
PROJECT_ROOT = "/Users/mac/liheci_project"
XFST_FILE    = os.path.join(PROJECT_ROOT, "fst/middle_grammar.xfst")
HFST_FILE    = os.path.join(PROJECT_ROOT, "fst/middle.hfst")
# ===========================================

def run_debug():
    print(f"=== 1. 检查源文件 ===")
    if not os.path.exists(XFST_FILE):
        print(f"❌ 错误：找不到规则文件: {XFST_FILE}")
        return
    print(f"✅ 规则文件存在: {XFST_FILE}")

    print(f"\n=== 2. 清理旧模型 ===")
    if os.path.exists(HFST_FILE):
        os.remove(HFST_FILE)
        print("已删除旧的 .hfst 文件。")
    
    print(f"\n=== 3. 开始编译 ===")
    # 使用绝对路径进行编译
    # 注意：source 后面跟绝对路径
    cmd = [
        'hfst-xfst',
        '-e', f'source {XFST_FILE}',
        '-e', f'save stack {HFST_FILE}',
        '-e', 'quit'
    ]
    
    print(f"执行命令: {' '.join(cmd)}")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True
        )
        
        # 打印编译器输出（如果有错误，这里会显示）
        if result.stdout.strip():
            print("--- 编译器输出 ---")
            print(result.stdout)
        
        if result.stderr.strip():
            print("--- 错误信息 ---")
            print(result.stderr)
            
    except Exception as e:
        print(f"❌ 无法执行 hfst-xfst 命令: {e}")
        return

    # 检查是否生成
    if not os.path.exists(HFST_FILE):
        print("❌ 编译失败！目标文件未生成。请检查上方的错误信息。")
        return
    
    size = os.path.getsize(HFST_FILE)
    print(f"✅ 编译成功！生成文件: {HFST_FILE} (大小: {size} bytes)")
    
    if size == 0:
        print("❌ 文件大小为 0，这是一个空模型！请检查 .xfst 脚本内容。")
        return

    print(f"\n=== 4. 冒烟测试 (Smoke Test) ===")
    # 测试用例："个@@" (代表 "个热水")
    # 前提：你的 .xfst 文件里必须定义 define ModChar "@" ;
    test_input = "个@@"
    
    print(f"正在测试输入: '{test_input}'")
    
    try:
        process = subprocess.Popen(
            ['hfst-lookup', '-q', HFST_FILE],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(input=test_input + "\n")
        
        print(f"FST 返回结果: {stdout.strip()}")
        
        if "+?" in stdout or "inf" in stdout or not stdout.strip():
            print("❌ 测试 FAIL: 模型拒绝了输入。")
            print("👉 请检查 middle_grammar.xfst 里的 'define ModChar' 是否改成了 \"@\"")
        else:
            print("✅ 测试 PASS: 模型工作正常！")
            print("🚀 现在请去运行: python3 src/main.py")

    except Exception as e:
        print(f"❌ 测试出错: {e}")

if __name__ == "__main__":
    run_debug()