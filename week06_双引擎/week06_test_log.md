# W6 双引擎边界测试记录

- 生成时间：2026-10-28 16:46:49
- 环境：MINGW64_NT-10.0-26200　Python：3.11.9
- 本地模型：qwen2.5:0.5b　本地地址：127.0.0.1:11434
- 测试问题：给《愚公移山》出一道 HSK4 阅读题，只要题干和四个选项
- 第2组做法：**真关掉 Ollama 服务**（讲义第 4 步原话）

## 一、三条路径

| # | 测试条件 | 实际走的引擎 | 耗时／回退 | 答案摘录 | 是否符合预期／怎么改的 |
|---|---|---|---|---|---|
| 1 | Ollama 开，prefer="local" | local | local ／ 3.73s ／ 回退: 否 ／ prefer=local | 好的，以下是《愚公移山》的题目以及四个选项，适合进行的 HSK4 阅读题： | 待你点评（示例：符合预期） |
| 2 | Ollama 已关闭，prefer="local"（真关服务） | api | api ／ 6.33s ／ 回退: 是 ／ prefer=local | **HSK4 阅读题** | 待你点评（示例：符合预期） |
| 3 | prefer="api" | api | api ／ 3.59s ／ 回退: 否 ／ prefer=api | **HSK4 阅读题** | 待你点评（示例：符合预期） |

## 二、回退日志原文（最关键的证据，别只写“成功了”）

### 第 2 组｜Ollama 已关闭，prefer="local"（真关服务）

```text
[首选引擎失败，自动切换] local → api：HTTPConnectionPool(host='127.0.0.1', port=11434): Max retries exceeded with url: /api/chat (Caused by NewConnectionError("HTTPConnection(host='127.0.0.1', port=11434): Failed to establish a new connection: [WinError 10061] 由于目标计算机积极拒绝，无法连接。"))
```

## 三、质量点评（自己写，不许空着）

1. 同一个问题，本地与云端的答案差在哪？各抄一句原话对比：

2. 本地速度 vs 云端速度（看上面的耗时）：

3. 这套封装对你的课堂意味着什么？哪类任务你会固定 `prefer="local"`，哪类固定 `"api"`：

