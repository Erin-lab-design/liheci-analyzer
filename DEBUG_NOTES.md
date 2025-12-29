# HFST 安装与运行调试记录

**日期**: 2025-12-28  
**项目**: liheci-analyzer  
**脚本**: `scripts/03.liheci_run_hfst.py`

## 问题总结

在 Windows 环境下运行 HFST 离合词分析脚本时遇到两个主要问题：
1. HFST 工具安装问题
2. 中文字符 UTF-8 编码问题

---

## 问题 1: HFST 安装失败

### 症状
```bash
pip install hfst
```
编译失败，报错：
```
fatal error C1083: 无法打开包括文件: "unistd.h": No such file or directory
error: command 'cl.exe' failed with exit code 2
```

### 根本原因
- PyPI 上的 `hfst` 包需要从源码编译
- Windows 下缺少必要的编译依赖（unistd.h 是 Unix 特有的头文件）
- PyPI 的预编译 wheels 只支持到 Python 3.6，不支持 Python 3.13

### 解决方案
使用预编译的 Windows 二进制文件：

1. **下载预编译版本**：
   - 已有文件：`D:\Erin\liheci-analyzer\hfst-3.16.2\hfst`
   - 或从 http://apertium.projectjj.com/win32/nightly/ 下载

2. **添加到系统 PATH**：
   ```powershell
   # 永久添加到用户环境变量
   $newPath = "D:\Erin\liheci-analyzer\hfst-3.16.2\hfst\bin"
   $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
   [Environment]::SetEnvironmentVariable("Path", "$currentPath;$newPath", "User")
   
   # 临时添加到当前会话
   $env:Path += ";D:\Erin\liheci-analyzer\hfst-3.16.2\hfst\bin"
   ```

3. **验证安装**：
   ```bash
   hfst-xfst --version
   hfst-lookup --version
   ```
   成功输出：`hfst-xfst.exe 0.1 (hfst 3.16.2)`

---

## 问题 2: UTF-8 编码错误

### 症状
脚本运行时，所有测试案例都显示：
```
[HFST] No liheci detected.
```

查看日志文件 `liheci_hfst_run.log` 发现：
```
HFST STDERR: terminate called after throwing an instance of 'IncorrectUtf8CodingException'
```

手动测试：
```powershell
echo "他睡了一个好觉" | hfst-lookup liheci_split.analyser.hfst
```
输出：
```
> ???????       ???????+?       inf
```
中文字符全部变成问号。

### 根本原因
1. Windows PowerShell 默认使用 GBK/CP936 编码
2. Python `subprocess.run()` 在 Windows 上默认使用系统编码
3. HFST 工具需要 UTF-8 编码的输入
4. 字符在传递过程中编码转换失败

### 解决方案

#### 步骤 1: 修改 Python 脚本
在 `scripts/03.liheci_run_hfst.py` 的 `subprocess.run()` 调用中添加 `encoding='utf-8'` 参数：

```python
# 修改前
result = subprocess.run(
    cmd,
    input=sentence + "\n",
    capture_output=True,
    text=True,
    check=False,
    timeout=HFST_TIMEOUT
)

# 修改后
result = subprocess.run(
    cmd,
    input=sentence + "\n",
    capture_output=True,
    text=True,
    encoding='utf-8',  # 添加此行
    check=False,
    timeout=HFST_TIMEOUT
)
```

#### 步骤 2: 设置 PowerShell 环境
在运行脚本前，设置控制台代码页为 UTF-8：

```powershell
chcp 65001
$OutputEncoding = [System.Text.Encoding]::UTF8
```

#### 步骤 3: 验证修复
测试命令：
```powershell
echo "他睡了一个好觉" | hfst-lookup liheci_split.analyser.hfst
```
成功输出：
```
> 他睡了一个好觉     睡觉+Lemma+Verb-Object+SPLIT        0.000000
```

---

## 问题 3: FST 文件路径配置

### 症状
脚本中硬编码的路径：
```python
HFST_FST_PATH = "fst_result_12.9/liheci_split.analyser.hfst"
```
但该目录不存在。

### 解决方案
1. **从 GitHub 拉取最新的 .hfst 文件**：
   ```bash
   git pull origin main
   ```
   成功拉取：
   - `liheci_split.analyser.hfst`
   - `liheci_split.generator.hfst`

2. **更新脚本中的路径**：
   ```python
   # 修改后
   HFST_FST_PATH = os.environ.get("LIHECI_SPLIT_FST", "liheci_split.analyser.hfst")
   ```

---

## 最终运行结果

### 成功指标
```
[Done] Processed 148 cases.
       Cases with at least one liheci: 147
       Total liheci analyses exported: 172
       Output TSV: liheci_hfst_outputs_retest.tsv
       Log file  : liheci_hfst_run.log
```

### 输出示例
```
[Case 1]
Gold stem   : [睡觉]
Sentence    : 昨天晚上我睡了一个好觉。
Gold label  : True
[HFST Analyses]: ['睡觉+Lemma+Verb-Object+SPLIT']
[Detected Lemmas]: ['睡觉']
```

### 识别到的离合词类型
- ✅ WHOLE 形式（连用）：睡觉、吃饭
- ✅ SPLIT 形式（插入）：睡了一个好觉、吃完饭
- ✅ REDUP 形式（重叠）：散散步、见一见面
- ✅ 多种类型：Verb-Object, PseudoV-O, Modifier-Head, SimplexWord

---

## 关键经验教训

### 1. Windows 环境下的 Python 包安装
- 优先查找预编译二进制文件，避免复杂的编译环境配置
- PyPI wheels 可能不支持最新 Python 版本
- Apertium 项目维护了 HFST 的 Windows 构建版本

### 2. 跨平台字符编码处理
- Windows 默认不是 UTF-8，需要显式配置
- Python `subprocess` 在不同平台的默认编码不同
- 始终显式指定 `encoding='utf-8'` 参数
- 设置系统环境（`chcp 65001`）作为辅助措施

### 3. 调试技巧
- 先手动测试外部命令（`echo "..." | hfst-lookup ...`）
- 检查日志文件中的详细错误信息
- 使用简单测试案例验证修复

### 4. Git 工作流
- 大型二进制文件（.hfst）可以提交到 Git
- 使用 `git pull` 同步团队成员的最新文件

---

## 环境配置检查清单

运行此项目前，请确保：

- [ ] 已安装 HFST 工具（3.16.2 或更高版本）
- [ ] HFST bin 目录已添加到系统 PATH
- [ ] PowerShell 代码页设置为 UTF-8 (`chcp 65001`)
- [ ] Python 虚拟环境已激活
- [ ] 已从 GitHub 拉取最新的 .hfst 文件
- [ ] 脚本中的文件路径配置正确

---

## 参考资源

- HFST 官方文档：https://hfst.github.io/
- HFST GitHub：https://github.com/hfst/hfst
- Windows 预编译版本：http://apertium.projectjj.com/win32/nightly/
- Python subprocess 文档：https://docs.python.org/3/library/subprocess.html
