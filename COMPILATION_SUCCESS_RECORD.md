# XFST 编译成功记录

**日期**: 2025-12-28  
**任务**: 编译 `scripts/02.liheci_split.xfst` 为 HFST 格式  
**结果**: ✅ 成功（从 4-5 小时卡死 → 14.67 秒完成）

---

## 问题背景

### 历史问题
之前尝试编译 XFST 文件时遇到严重性能问题：
- 编译过程卡住 4-5 小时无响应
- 不确定是编译失败还是正常慢

### 编译需求
- **源文件**: `D:\Erin\liheci-analyzer\scripts\02.liheci_split.xfst`
- **目标**: 生成 `.hfst` 文件用于离合词分析
- **要求**: 在 scripts 目录编译，不覆盖根目录的原文件

---

## 编译过程详解

### 步骤 1: 确认环境和文件

#### 检查 HFST 是否可用
```powershell
hfst-xfst --version
```

**输出**:
```
hfst-xfst.exe 0.1 (hfst 3.16.2)
```

#### 检查源文件
```powershell
cd D:\Erin\liheci-analyzer\scripts
ls 02.liheci_split.xfst
```

**文件信息**:
- 大小: 50,358 字节
- 行数: 922 行
- 包含 128 个离合词的定义

---

### 步骤 2: 尝试不同的编译命令

#### ❌ 尝试 1: 错误的 -f 参数
```powershell
hfst-xfst -f 02.liheci_split.xfst
```

**错误**:
```
Error: Could not parse format name from string 02.liheci_split.xfst
```

**原因**: `-f` 参数是用来指定输出格式（foma, openfst-tropical 等），不是用来指定输入文件。

---

#### ❌ 尝试 2: 管道输入（PowerShell）
```powershell
Get-Content 02.liheci_split.xfst | hfst-xfst
```

**结果**: 
- 执行非常快（约 1.78 秒）
- 但没有生成任何 .hfst 文件

**原因**: 命令执行了但可能输出没有正确保存，或者需要其他参数。

---

#### ❌ 尝试 3: Unix 风格重定向（在 PowerShell 中不支持）
```powershell
hfst-xfst < 02.liheci_split.xfst
```

**错误**:
```
"<"运算符是为将来使用而保留的。
RedirectionNotSupported
```

**原因**: PowerShell 不支持 `<` 重定向运算符。

---

#### ✅ 成功方法: 使用 -F 参数

查看帮助文档找到正确参数：
```powershell
hfst-xfst --help | Select-Object -First 30
```

**关键发现**:
```
-F, --scriptfile=FILE      Read commands from FILE, and quit
```

**正确命令**:
```powershell
cd D:\Erin\liheci-analyzer\scripts
hfst-xfst -F 02.liheci_split.xfst
```

---

### 步骤 3: 完整的编译命令（带计时和检查）

```powershell
# 设置 PATH（如果需要）
$env:Path = "D:\Erin\liheci-analyzer\hfst-3.16.2\hfst\bin;" + $env:Path

# 切换到 scripts 目录
cd D:\Erin\liheci-analyzer\scripts

# 开始编译（带计时）
Write-Host "开始编译..." -ForegroundColor Yellow
$start = Get-Date

hfst-xfst -F 02.liheci_split.xfst

$end = Get-Date
Write-Host "`n✅ 编译完成！耗时: $(($end - $start).TotalSeconds) 秒" -ForegroundColor Green

# 列出生成的文件
Write-Host "`n生成的文件：" -ForegroundColor Cyan
ls *.hfst | Format-Table Name, @{N='Size(MB)';E={[math]::Round($_.Length/1MB,2)}}, LastWriteTime
```

---

## 编译结果

### 成功指标

**编译时间**: 14.67 秒 ⚡

**编译输出**（部分）:
```
Defined 'Punct'
Defined 'AnyChar'
Defined 'LegalIns'
Defined 'RedupMid'
Defined 'L001WholePat'
Defined 'L001SplitPat'
...
Defined 'L128Whole'
Defined 'L128Split'
? bytes. 712 states, 456360 arcs, ? paths
```

**生成的文件**:
```
Name                         Size(MB)  LastWriteTime
----                         --------  -------------
liheci_split.analyser.hfst   7.00      2025/12/28 21:58:11
liheci_split.generator.hfst  6.99      2025/12/28 21:58:10
```

**FST 统计信息**:
- **States**: 712
- **Arcs**: 456,360
- **Paths**: 未知（动态）

---

## 测试编译结果

### 问题 1: UTF-8 编码问题

#### ❌ 初次测试失败
```powershell
echo "他睡了一个好觉" | hfst-lookup liheci_split.analyser.hfst
```

**输出**:
```
> ???????       ???????+?       inf
```

**问题**: 中文字符在 PowerShell 中默认使用 GBK 编码，导致乱码。

---

#### ✅ 解决方案: 设置 UTF-8
```powershell
# 设置控制台代码页为 UTF-8
chcp 65001

# 设置 PowerShell 输出编码
$OutputEncoding = [System.Text.Encoding]::UTF8

# 再次测试
echo "他睡了一个好觉" | hfst-lookup liheci_split.analyser.hfst
```

**改进的输出**（虽然中文显示仍有问题，但识别正常）:
```
> 他睡了一个好觉     睡觉+Lemma+Verb-Object+SPLIT        0.000000
```

---

### 问题 2: 需要更可靠的测试方法

直接在 PowerShell 用 echo 测试中文有显示问题，创建 Python 测试脚本。

#### 创建测试脚本

**文件**: `scripts/test_compiled_hfst.py`

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""快速测试脚本 - 测试 scripts 目录下新编译的 HFST 文件"""

import subprocess

test_cases = [
    ("他睡了一个好觉", "睡觉", "SPLIT"),
    ("我们去散散步", "散步", "REDUP"),
    ("昨天吃了饭", "吃饭", "SPLIT"),
    ("他在洗澡", "洗澡", "WHOLE"),
]

HFST_FST = "liheci_split.analyser.hfst"

print("=" * 60)
print("测试 scripts 目录下新编译的 HFST 文件")
print("=" * 60)

for sentence, expected_lemma, expected_form in test_cases:
    print(f"\n句子: {sentence}")
    print(f"期望: {expected_lemma} ({expected_form})")
    
    try:
        result = subprocess.run(
            ["hfst-lookup", HFST_FST],
            input=sentence + "\n",
            capture_output=True,
            text=True,
            encoding='utf-8',  # 关键：显式指定 UTF-8
            timeout=5
        )
        
        # 解析输出
        found = False
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or line.startswith(">"):
                continue
            
            parts = line.split()
            if len(parts) >= 2:
                analysis = parts[1]
                if "+Lemma" in analysis:
                    print(f"✓ 识别: {analysis}")
                    
                    if expected_lemma in analysis and expected_form in analysis:
                        found = True
        
        if not found:
            print("✗ 未识别到期望的离合词")
            
    except Exception as e:
        print(f"✗ 错误: {e}")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)
```

---

#### ✅ 运行测试

```powershell
cd D:\Erin\liheci-analyzer\scripts
& 'D:/Erin/.venv/Scripts/python.exe' test_compiled_hfst.py
```

**测试结果**: 全部通过 ✅

```
============================================================
测试 scripts 目录下新编译的 HFST 文件
============================================================

句子: 他睡了一个好觉
期望: 睡觉 (SPLIT)
✓ 识别: 睡觉+Lemma+Verb-Object+SPLIT

句子: 我们去散散步
期望: 散步 (REDUP)
✓ 识别: 散步+Lemma+Verb-Object+SPLIT+REDUP

句子: 昨天吃了饭
期望: 吃饭 (SPLIT)
✓ 识别: 吃饭+Lemma+Verb-Object+SPLIT

句子: 他在洗澡
期望: 洗澡 (WHOLE)
✓ 识别: 洗澡+Lemma+Verb-Object+WHOLE

============================================================
测试完成
============================================================
```

---

## 问题总结与解决方案

### 问题 1: 不知道正确的编译命令

**症状**: 
- `-f` 参数报错
- 管道方式没有输出文件
- Unix 重定向不支持

**解决**:
1. 使用 `hfst-xfst --help` 查看文档
2. 找到正确参数 `-F, --scriptfile=FILE`
3. 使用 `hfst-xfst -F 02.liheci_split.xfst`

**关键命令**:
```powershell
hfst-xfst -F 02.liheci_split.xfst
```

---

### 问题 2: PowerShell 中文编码问题

**症状**: 
- `echo "中文" | hfst-lookup` 显示乱码 `???????`

**根本原因**:
- Windows PowerShell 默认使用 GBK/CP936 编码
- HFST 工具需要 UTF-8 输入

**解决方案**:
```powershell
# 临时设置当前会话
chcp 65001
$OutputEncoding = [System.Text.Encoding]::UTF8

# 或在 Python 中显式指定编码
subprocess.run(..., encoding='utf-8')
```

---

### 问题 3: 之前编译卡死 4-5 小时

**可能原因**:
1. 旧版本 HFST 性能问题
2. 系统资源不足
3. 编译命令不正确导致卡住

**现在解决**:
- 使用 HFST 3.16.2
- 正确的 `-F` 参数
- 结果：14.67 秒完成 ⚡

**性能对比**:
```
之前：4-5 小时（卡死）
现在：14.67 秒
提升：约 1000+ 倍
```

---

## 关键命令速查表

### 编译 XFST 文件
```powershell
# 切换到 scripts 目录
cd D:\Erin\liheci-analyzer\scripts

# 确保 HFST 在 PATH 中
$env:Path += ";D:\Erin\liheci-analyzer\hfst-3.16.2\hfst\bin"

# 编译（正确方法）
hfst-xfst -F 02.liheci_split.xfst

# 查看生成的文件
ls *.hfst
```

---

### 测试编译结果

#### 方法 1: PowerShell（简单测试）
```powershell
# 设置 UTF-8
chcp 65001
$OutputEncoding = [System.Text.Encoding]::UTF8

# 测试
echo "他睡了一个好觉" | hfst-lookup liheci_split.analyser.hfst
```

**Note**: This method may have display issues with Chinese characters in PowerShell, but recognition works correctly.

---

#### 方法 2: Python One-liner（推荐 - Recommended）
```powershell
# Single command test with proper UTF-8 encoding
D:/Erin/.venv/Scripts/python.exe -c "import subprocess; result = subprocess.run(['hfst-lookup', 'scripts/liheci_split.analyser.hfst'], input='他昨天睡了一个好觉\n', capture_output=True, text=True, encoding='utf-8'); print(result.stdout)"
```

**Output**:
```
他昨天睡了一个好觉      睡觉+Lemma+Verb-Object+SPLIT    0.000000
```

**Advantages**:
- ✅ Proper UTF-8 encoding handling
- ✅ Clean, readable output with Chinese characters
- ✅ No need to create separate test file
- ✅ Can be used in any directory (uses relative path `scripts/`)

---

#### 方法 3: Python Test Script（完整测试 - Comprehensive Testing）
```powershell
# Run full test suite
& 'D:/Erin/.venv/Scripts/python.exe' scripts/test_compiled_hfst.py
```

---

### 常用检查命令

```powershell
# 查看 HFST 版本
hfst-xfst --version

# 查看帮助
hfst-xfst --help

# 检查文件大小
Get-ChildItem *.hfst | Select-Object Name, Length, LastWriteTime

# 查看文件行数
Get-Content 02.liheci_split.xfst | Measure-Object -Line
```

---

## 最佳实践建议

### 1. 编译前检查
- ✅ 确认 HFST 已安装并在 PATH 中
- ✅ 确认源文件存在且格式正确
- ✅ 确认有写入权限

### 2. 编译时注意
- ✅ 使用 `-F` 参数而不是 `-f`
- ✅ 在正确的目录下执行
- ✅ 记录编译时间和输出

### 3. 测试时注意
- ✅ 设置正确的字符编码（UTF-8）
- ✅ 使用 Python 脚本进行可靠测试
- ✅ 测试多种离合词类型（WHOLE/SPLIT/REDUP）

### 4. 文件管理
- ✅ 区分开发版本（scripts/）和生产版本（根目录）
- ✅ 保留测试脚本便于后续验证
- ✅ 记录编译时间和 FST 统计信息

---

## 附录：XFST 文件结构

### 文件概览
```
02.liheci_split.xfst (922 行)
├── 符号定义 (4 行)
│   ├── Punct (标点符号)
│   ├── AnyChar (任意字符)
│   ├── LegalIns (合法插入字符)
│   └── RedupMid (重叠中间字符)
├── 离合词定义 (128 个 × ~7 行 = ~896 行)
│   └── 每个离合词包含:
│       ├── WholePat (整体模式)
│       ├── SplitPat (分离模式)
│       ├── RedupPat (重叠模式，部分)
│       ├── Whole (整体转导器)
│       ├── Split (分离转导器)
│       └── Redup (重叠转导器，部分)
└── 组合和保存 (3 行)
    ├── regex 组合所有转导器
    ├── save generator
    └── save analyser
```

### FST 类型统计
- **Verb-Object**: 113 个
- **PseudoV-O**: 4 个
- **SimplexWord**: 3 个
- **Modifier-Head**: 8 个

---

## 总结

### 成功要素
1. ✅ 找到正确的命令参数（`-F`）
2. ✅ 解决字符编码问题（UTF-8）
3. ✅ 创建可靠的测试方法（Python 脚本）
4. ✅ 使用新版 HFST 3.16.2

### 性能提升
```
编译时间：4-5 小时 → 14.67 秒（提升 1000+ 倍）
```

### 输出质量
- 712 states, 456,360 arcs
- 识别准确率：100%（测试用例）
- 支持 WHOLE/SPLIT/REDUP 三种形式

### 可复现性
所有命令和步骤已记录，可重复执行，适用于：
- 修改 XFST 规则后重新编译
- 在其他机器上部署
- 持续集成/持续部署（CI/CD）
