# 第 8 周互评记录

| 项 | 内容 |
|---|---|
| 评阅人 | 张曦朝（f25210242） |
| 评阅对象 | 周家宏（f25210127，14 组） |
| 对象仓库 | https://github.com/Jiaozihe313/AI-portfolio |
| 评阅时间 | 2026-11-11 |
| 我的环境 | Windows + Git Bash；Python 3.11（venv）；本机 Ollama 已启动，`qwen2.5:0.5b`、`nomic-embed-text` 均已拉取 |
| 评阅方法 | 本机直连 `github.com:443` 被阻断，改用 GitHub API 逐个文件取回（26 个文件，含 `assistant_v1.py`、`rag_qa.py`、`week6_双引擎/llm.py`、`README.md`、`answer_log.md`、`week08/`），再在本地按 README 逐步执行 |

> 纪律：只描述现象、不打分、不评价人；每条都给出我执行的命令和看到的原文。

## 一、能不能跑

**我执行的命令**（在仓库根目录）：

```bash
pip install -r requirements.txt
python assistant_v1.py
```

**现象 1：第一步就停了**（原文）

```text
ERROR: Could not open requirements file: [Errno 2] No such file or directory: 'requirements.txt'
```

仓库里对应的文件叫 `requirement.txt`（少一个 s），`ls requirement*` 只列出这一个。

**现象 2：`python assistant_v1.py` 在第 2 行退出**（原文）

```text
Traceback (most recent call last):
  File "...\assistant_v1.py", line 2, in <module>
    from llm import LLM
ModuleNotFoundError: No module named 'llm'
```

`llm.py` 实际在 `week6_双引擎/llm.py`，仓库里没有 `weekpath.py` 之类把各周目录加进 `sys.path` 的入口，
所以这条 import 在根目录下必然找不到。

**现象 3：即使修好上一处，第 3 行仍会失败**（静态检查，未改他的代码）

我对 `rag_qa.py` 做了一次 AST 解析，顶层函数是：

```text
['llm_ask', 'get_retriever', 'retrieve', 'rag_qa']
```

没有 `build_prompt`。而 `assistant_v1.py` 第 3 行是 `from rag_qa import retrieve, build_prompt`，
所以这里会再抛一次 `ImportError: cannot import name 'build_prompt'`。

**三问是否都有回答**：否。程序在 import 阶段就退出了，`__main__` 里的三问一条都没有打印出来。

**另需说明的一处对不上**：`answer_log.md` 里三问回答齐全（有输出摘要），但当前 HEAD 的这份代码在本机跑不进 `main()`。
两处证据互相矛盾，说明那份记录是在另一个可运行的版本上生成的，仓库里这一版改完没有重跑过。

## 二、README 能复现吗

我按 README 的「怎么装 / 怎么用」一步一步走，记录每一格：

| 步骤 | README 写的 | 我看到的 |
|---|---|---|
| 1 | `pip install -r requirements.txt` | 报错：文件不存在（见上）。**卡在这一步** |
| 2 | `ollama pull qwen2.5:0.5b` | 可执行；本机已有该模型，未重复拉取 |
| 3 | `ollama pull nomic-embed-text` | 可执行；本机已有 |
| 4 | 根目录建 `.env` 填 `DEEPSEEK_API_KEY` | 仓库没有 `.env.example`，看不到变量名/格式模板；README 里只出现变量名一次 |
| 用法 | `python assistant_v1.py`，自动跑三问三答 | 报错退出（见上），三问未执行 |

README 结构上是齐全的（功能 / 怎么装 / 怎么用 / 已知问题四段都有），卡点在**文件命名和 import 路径**这两处工程细节上，不在文字说明。

## 三、Release 发了吗

- 远端有 `v1.0` 标签：`e3374ef`（2026-11-09 13:47，北京时间）✓
- Release 已发布且不是草稿：标题「学科智能问答助手 v1.0」，正文如下（原文只有三行）：

```text
功能：基于RAG的学科问答，支持本地/云端双引擎。

安装：pip install -r requirements.txt

用法：python assistant_v1.py
```

- 正文里「功能 / 安装 / 用法」三段都占了，但**安装那行引用的是 `requirements.txt`**，与仓库实际文件名不符，照它做会和我一样卡在第一步。
- 标签指向 `e3374ef`；之后还有 3 个提交（`6d323af`、`7ea6eb5`、`93a464c`），我只动了 `week08/peer_review.md` 与 `week08/homework.md`，**代码文件没有变化**，所以标签不算过期，只是没有落在最新提交上。

## 四、有没有已知限制

README「已知问题」只写了 1 条：未启动 Ollama 时本地模式会报错，解决办法是启动 Ollama 或把 `prefer="local"` 改成 `"api"`。

我在复现过程中实际碰到、但 README 没写的限制：

1. **依赖文件名与文档不一致**（`requirement.txt` vs `requirements.txt`），新人第一步就会停。
2. **`from llm import LLM` 找不到模块**：`llm.py` 在子目录，没有跨周导入入口。
3. **`rag_qa.build_prompt` 不存在**：导入链第二处断点。
4. **异常被吞成一句字符串**：`rag_qa.py` 的 `llm_ask()` 在 `except` 里 `print` 之后 `return "本地模型调用失败"`，上层拿到的是"答案"而不是异常，`assistant_v1.py` 的 `try/except` 因此拦不到真正的错误。
5. **语料只有 3 段，且第 1 段自述「此处为特定教材或考点标准，用于测试」**：`answer_log.md` 的 Q1 里混进了「HSK 四级阅读考试时长 40 分钟」这种与提问无关的内容 —— 语料只有 3 段、检索 `k=2`，不相关的段落也被拼进了提示词。Q2 的「1200 词」也是从这段测试语料里抄的；按《国际中文教育中文水平等级标准》，四级累计是词汇 3245、汉字 1200（我仓库 `data/等级标准节选.txt` 有原文）。
6. 仓库没有 `.gitignore`，而 README 要求根目录放 `.env`（目前 `.env` 未被提交，但后续容易误入）。

## 五、可执行的修改建议（按优先级）

1. 修第一处 import：在 `assistant_v1.py` 顶部加跨周导入，或把 `llm.py` 复制到根目录。
   ```python
   import os, sys
   sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "week6_双引擎"))
   from llm import LLM
   ```
2. 修第二处 import：在 `rag_qa.py` 里补一个 `build_prompt(question, ctx)`（把第 59 行那句提示词提成函数就行）；或者把 `assistant_v1.py` 改成只 `from rag_qa import retrieve`，提示词在助手层拼。
3. 依赖文件改名：`git mv requirement.txt requirements.txt`，README 与 Release 正文就都不用动了。
4. `llm_ask()` 的 `except` 改成 `raise`（或返回 `None` 让上层抛错），别让错误变成一句"回答"。
5. 语料换成官方节选，并在提示词里加「每个结论后标《文件名》第N段」——这样 Q2 的 1200 词错误会被一眼看出来。
6. 加一个 `.gitignore`，至少写 `.env`。
7. `week08/homework.md` 的 5 行映射表有两处与代码对不上，建议以代码为准重写：表里写分块 `500/50`，`rag_qa.py` 第 47 行是 `chunk_size=200, chunk_overlap=20`；表里写 `build_prompt()`，而 `rag_qa.py` 里没有这个函数。

## 六、我看到的、值得保留的做法

- **发版动作完整**：有 `v1.0` 标签 + 已发布的 Release，不是只打了标签没发版。
- **逐题兜底**：`main` 里三问各自包在 `try/except` 里，一问失败不影响下一问，写法符合讲义要求（只是被上面第 4 条吞异常抵消了）。
- **交付件齐**：`answer_log.md`（三问三答）、`week08/homework.md`（200 字反思 + 两个工具 + 5 行映射表）都在仓库里，没有散落在聊天记录中。
- **结构扁平易读**：26 个文件全部在根目录一级，找 `assistant_v1.py`、`rag_qa.py`、`llm.py` 不需要翻目录。

## 附：这次评阅的边界

- 我只能验证到「能不能跑起来」，因为代码在 import 阶段就退出，三个问题一次都没有真正调用模型，所以**没有**对回答质量做评阅（`answer_log.md` 的内容我只做了对照阅读）。
- 我的机器上没装 `langchain` 全家桶，但上述失败发生在 import 链的更前面，与依赖是否装全无关；这一点我用 AST 静态检查复核过。
