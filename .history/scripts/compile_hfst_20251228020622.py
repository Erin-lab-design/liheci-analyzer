#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
compile_hfst.py - HFST 编译管理脚本

使用方法：
    python3 scripts/compile_hfst.py scripts/02.liheci_split.xfst
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

def compile_hfst(xfst_file, log_file=None):
    """
    编译 XFST 文件为 HFST
    
    Args:
        xfst_file: XFST 源文件路径
        log_file: 日志文件路径（可选）
    """
    xfst_path = Path(xfst_file)
    
    if not xfst_path.exists():
        print(f"❌ 错误：找不到文件 {xfst_file}")
        return False
    
    if log_file is None:
        log_file = f"hfst_compile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    log_path = Path(log_file)
    
    print(f"🚀 开始编译：{xfst_file}")
    print(f"📝 日志文件：{log_file}")
    print(f"⏰ 开始时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 60)
    
    try:
        # 打开日志文件
        with log_path.open('w', encoding='utf-8') as log_f:
            # 写入编译信息头
            log_f.write(f"编译开始时间：{datetime.now()}\n")
            log_f.write(f"源文件：{xfst_file}\n")
            log_f.write("-" * 60 + "\n")
            log_f.flush()
            
            # 启动编译进程
            process = subprocess.Popen(
                ['hfst-xfst'],
                stdin=open(xfst_path, 'r', encoding='utf-8'),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1  # 行缓冲
            )
            
            # 实时读取输出
            for line in process.stdout:
                # 同时打印到终端和写入日志
                print(line, end='')
                log_f.write(line)
                log_f.flush()
            
            # 等待进程结束
            return_code = process.wait()
            
            end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if return_code == 0:
                msg = f"\n✅ 编译成功完成！\n⏰ 结束时间：{end_time}\n"
                print(msg)
                log_f.write(msg)
                return True
            else:
                msg = f"\n❌ 编译失败（返回码: {return_code}）\n⏰ 结束时间：{end_time}\n"
                print(msg)
                log_f.write(msg)
                return False
                
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断编译（Ctrl+C）")
        if process:
            process.terminate()
        return False
    except Exception as e:
        print(f"\n❌ 编译过程中出错：{e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法：python3 scripts/compile_hfst.py <xfst文件> [日志文件]")
        print("示例：python3 scripts/compile_hfst.py scripts/02.liheci_split.xfst")
        sys.exit(1)
    
    xfst_file = sys.argv[1]
    log_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    success = compile_hfst(xfst_file, log_file)
    sys.exit(0 if success else 1)
