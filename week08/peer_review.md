# 第 8 周互评记录

| 项 | 内容 |
|---|---|
| 评阅人 | 陈心怡（f25210205） |
| 评阅对象 | 陈丽琪（f25210102） |
| 对象仓库 | https://github.com/chen99894/ai-portfolio |
| 评阅时间 | 2026-11-11 |
| 我的环境 | Windows 11 + Git Bash；Python 3.11；本机 Ollama 已启动，`qwen2.5:0.5b`、`nomic-embed-text` 均已拉取 |
| 评阅方法 | `git clone` 取回仓库（36 个文件，单次提交 `2b82864 Add files via upload`），在仓库根目录按 README 逐步执行 |

> 纪律：只描述现象、不打分、不评价人；每条给出我执行的命令和看到的原文。

## 一、能不能跑

**我执行的命令**（仓库根目录）：

```bash
pip install -r requirements.txt
python assistant_v1.py
```

**现象：`python assistant_v1.py` 在第 13 行退出**（原文）

```text
Traceback (most recent call last):
  File "...\assistant_v1.py", line 13, in <module>
    import weekpath  # noqa: E402  让跨周 import 生效（llm 在 week06、rag_qa 在 week07）
    ^^^^^^^^^^^^^^^
ModuleNotFoundError: No module named 'weekpath'
```

`assistant_v1.py` 第 12 行把「仓库的上一级目录」加进 `sys.path`，第 13 行 import `weekpath`，
但这个仓库里**没有 `weekpath.py`**，上一级目录里也没有。同理 `from llm import LLM` 也拿不到
（`llm.py` 在 `week06/` 子目录，本来要靠 `weekpath` 把各周目录加进 `sys.path`）。

**缺失文件清单**（`ls` 与 `git ls-files` 结果一致）

| 代码/文档引用到 | 仓库里实际 | 影响 |
|---|---|---|
| `weekpath.py` | 无 | 第 13 行 import 直接失败；W7 的 `rag_qa.py` 第 24 行同样失败 |
| `data/等级标准节选.txt` | 无 `data/` 目录 | `rag_qa.py` 第 28 行 `CORPUS = weekpath.data_path("等级标准节选.txt")` 指向不存在的路径 |
| `requirements.txt` | 无 | README「怎么装」第 1 步无法执行 |
| `.env.example`、`.gitignore` | 均无 | README 第 4 步 `cp .env.example .env` 无法执行；README 写的「`.env` 已在 `.gitignore` 里」在仓库里找不到对应文件 |
| `week08_助手v1.0/` 目录 | 无 | README 与 `RELEASE_v1.0.md` 里的运行命令都写 `cd week08_助手v1.0`，而 `assistant_v1.py` 就在根目录 |

**三问是否都有回答**：否。程序在 import 阶段退出，`run_demo()` 一次都没进入。

**需要说明的是**：这只是「缺脚手架文件」，不是代码逻辑错。`assistant_v1.py` 本身结构是标准的粘合层
（`answer()` 只有十几行：检索 → 拼提示词 → `llm.ask()`），`use_rag` 开关、`prefer` 透传、
检索失败降级、逐题 `try/except` 都在；把上面五个缺件补齐，按代码看是能跑通的。

## 二、README 能复现吗

| 步骤 | README 写的 | 我看到的 |
|---|---|---|
| 1 | `pip install -r requirements.txt` | 仓库根目录没有该文件。**卡在这一步** |
| 2 | `ollama pull qwen2.5:0.5b && ollama pull nomic-embed-text` | 可执行；本机已有两个模型，未重复拉取 |
| 3 | `cp .env.example .env` 填 `DEEPSEEK_API_KEY` | 没有 `.env.example`；也没有 `.gitignore`，但 README 说 `.env` 已被它排除 |
| 用法 | `cd week08_助手v1.0 && python assistant_v1.py` | 没有 `week08_助手v1.0` 目录；`assistant_v1.py` 在仓库根目录 |
| 用法 | `python assistant_v1.py --prefer api` / `--ask "…" --no-rag` | 参数写法在代码里确实实现了（`main()` 里解析 `--ask/--no-rag/--prefer`），只是目录前提不成立 |

README 的文字质量本身是好的：四段齐全、命令行一条条列出来、已知问题写到具体数字（见第四项），
问题集中在**仓库上传的内容和 README 描述的不是同一套目录结构**——像是把本地 `week08_助手v1.0/` 里的
几个文件单独传了上来，`weekpath.py`、`data/`、`requirements.txt`、`.gitignore` 这些"项目根"的东西没跟着来。

`RELEASE_v1.0.md` 里的安装/用法命令（`python -m pip install -r week08_助手v1.0/requirements.txt`、
`python week08_助手v1.0/assistant_v1.py`）指向的是同一个不存在的目录。

## 三、Release 发了吗

| 检查点 | 现象 |
|---|---|
| 远端 `v1.0` 标签 | **没有**。`git tag -l` 输出为空；GitHub API `tags` 返回 `[]` |
| Release 页面 | **没有**。GitHub API `releases` 返回 `[]` |
| 仓库里有没有发版内容 | 有，`RELEASE_v1.0.md`（89 行，功能/安装/用法/已知问题都写了，质量不错） |

也就是说：**发版文案已经写好并入库，但"打标签 + 发 Release"这两个动作还没做**。
按讲义第 10 页，这两步是作业 2 的硬指标。

## 四、有没有已知限制

README「已知问题」写了 4 条，是我这次看到的几份里写得最实的一份：

1. 本地 `qwen2.5:0.5b` 读表格弱，会把相邻两列读串（举例：把语法点答成 210、把音节 1800 当成语法点）；
2. 知识库只有两份资料，问库外问题会如实回「资料中未提及」；
3. 换 `data/` 里的文本必须重建向量库；
4. 未启动 Ollama 时本地模式报错。

我在复现中碰到、但 README 没写的情况：

1. `requirements.txt` 不存在（与「怎么装」第 1 步冲突）。
2. `weekpath.py` 不存在（import 链在第一步就断）。
3. `data/` 不存在（语料路径指向空处）。
4. `.env.example` / `.gitignore` 不存在（与第 4 步和安全声明冲突）。
5. 仓库里只有一次提交（`Add files via upload`），没有打标签，所以「代码改了但库没重建」这类版本问题在仓库里无从判断。

## 五、可执行的修改建议（按优先级）

1. **补 5 个文件**：`weekpath.py`、`data/`（放 `等级标准节选.txt` 与 `愚公移山.txt`）、`requirements.txt`、
   `.env.example`、`.gitignore`。这五个补上，README 就能照着跑了。
2. 或改代码里的路径：把 `assistant_v1.py` 第 12 行改成
   ```python
   sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
   sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "week06"))
   ```
   并把 `import weekpath` 换成直接 `from llm import LLM`，README 里再删掉 `cd week08_助手v1.0`。
3. 目录统一：README、`RELEASE_v1.0.md`、代码注释里出现三种路径写法（`week08_助手v1.0/`、根目录、`data/`），
   建议只留一种，按实际仓库结构写。
4. 打标签 + 发 Release：`git tag -a v1.0 -m "学科智能问答助手 v1.0" && git push origin main --tags`，
   再在网页 Releases 里选 `v1.0`，正文直接用现有的 `RELEASE_v1.0.md`。
5. 补 `.gitignore`（至少 `.env`、`chroma_db/`、`__pycache__/`）——README 已经声称有了，文件要对得上。
6. `rag_qa.py` 里用 `weekpath.data_path()` 取语料是好事（不依赖工作目录），但要在 README 写清
   `data/` 是必须自带的目录，否则 clone 下来就是空的。

## 六、我看到的、值得保留的做法

- **不装 langchain 也能把 RAG 四步跑完整**：`rag_qa.py` 用标准库 `urllib` 直连 Ollama 的 `/api/embed`，
  自己做余弦检索，向量落 `chroma_db/vectors.json`，并在注释里写明「接口与讲义一致，装上 langchain 只需换 `get_retriever()` 内部」——
  这是有意识的工程取舍，不是抄骨架。
- **`RETRIEVE` 降级**：`retrieve_chunks_safe()` 检索失败时打印 `[warn]` 并退回纯对话，演示不会整场挂掉。
- **`answer_log.md` 是 6 组而不是 3 组**：三问 × 开/关各一次，每组带耗时、引擎、引据和一句点评，
  其中还老实写了「关 RAG 时把汉字累计 1200 记成词汇量」这种自己发现的错。
- **文档密度高**：`rag_mapping.md`、`rag_pipeline_mapping.md`、`w8_项目设计`、`w8_说明`、`w9_预习`、`reflect.md`、`peer_review.md` 都在，
  说明这周是按「交付件」在准备，不是只交了代码。

## 七、第 9 周预习：我希望助手拥有的两个工具

第 9 周是「工具调用」：让助手不只回话，还能查表、算分、执行动作。我挑的两个工具，
都必须能被机器精确验证，不靠模型"感觉"。

### 工具 1：`grade_lookup(指标, 级别, 口径)`

| 项 | 说明 |
|---|---|
| 用途 | 回答「HSK 几级要多少词/字/语法点」，把必须精确的数字交给查询而不是模型记忆 |
| 输入 | `指标 ∈ {音节, 汉字, 词汇, 语法点}`、`级别 ∈ {一级…六级, 七—九级}`、`口径 ∈ {新增, 累计}` |
| 输出 | `{值, 出处: "《等级标准节选.txt》第N段", 行原文}`；查无此项时返回 `{值: null, 原因}` |
| 为什么值得工具化 | 这次互评里正好看到代价：本地 0.5b 会把「76/286」读串，把语法点答成 210。查询是确定性的，不该交给概率 |

### 工具 2：`vocab_pick(等级, 词性, 数量, 题型)`

| 项 | 说明 |
|---|---|
| 用途 | 备课「按 HSK 等级挑词 + 直接出练习」，替代人工翻 CSV |
| 输入 | `等级 ∈ {3,4,5,6}`、`词性`（可空）、`数量 ≤ 20`、`题型 ∈ {造句, 填空, 释义}` |
| 输出 | `{词条: [...], 题目: [...], 答案: [...], 出处: "《生词表.csv》第N行"}` |
| 为什么值得工具化 | 词汇范围必须严格落在 `data/生词表.csv` 内（一个超纲词就能毁掉一节课），数量与等级筛选是纯过滤，模型容易多给或少给 |

两个工具的共同点：输入是闭集（枚举 + 上限），输出带出处字段，失败时明确返回「查无此项」而不是编一个答案。

## 附：这次评阅的边界

- 我停在「能不能跑起来」这一层：代码在 import 阶段就退出，三问一次都没真正调用模型，
  所以**没有**评阅回答质量（`answer_log.md` 我只做了对照阅读）。
- 我的机器上没装 `langchain`，但按她 README 的说法本来就不需要；上述失败发生在 `weekpath` 这步，与依赖无关。
