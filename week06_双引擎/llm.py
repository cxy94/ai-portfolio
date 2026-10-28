# -*- coding: utf-8 -*-
"""llm.py —— W6 双引擎统一入口：本地 Ollama ＋ 云端 DeepSeek，一个 prefer 参数切换

    from llm import LLM
    print(LLM().ask("给《愚公移山》出一道 HSK4 阅读题", prefer="local"))
    print(LLM().ask("设计一份 45 分钟的读写课教案", prefer="api"))

命令行（课堂三条路径就是它）：
    python llm.py "给《愚公移山》出一道 HSK4 阅读题" --prefer local
    python llm.py "同一个问题" --prefer api

设计纪律（讲义第四、七节）：
    · 不吞异常：except 里必须打印原因，禁止 pass、禁止返回空字符串
    · 回退必须双向：prefer="local" 本地挂→切云端；prefer="api" 云端挂→切本地
    · 返回类型统一为 str：上层才能无差别使用两个引擎
"""
from __future__ import annotations

import argparse
import os
import sys
import time

# 跨周导入固定三行（讲义第 7 节）：让 W7/W8 的 from llm import LLM 找得到，
# 同时把 .env 加载好，免得到处重复 load_env()。
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
try:
    import weekpath
    weekpath.load_env()
except Exception:                      # 没有 weekpath（单独拷贝出去跑）也不影响
    pass

DEFAULT_LOCAL_MODEL = "qwen2.5:0.5b"
DEFAULT_LOCAL_HOST = "127.0.0.1:11434"   # 用 127.0.0.1 而不是 localhost：
                                         # Windows 上 localhost 可能解析到 IPv6 ::1，而 Ollama 只听 IPv4
DEFAULT_LOCAL_TIMEOUT = 60.0             # 首次装载可能 30 秒，必须留够
DEFAULT_API_MODEL = "deepseek-chat"
DEFAULT_API_BASE = "https://api.deepseek.com/v1"
DEFAULT_API_TIMEOUT = 120.0


class LLMError(RuntimeError):
    """两个引擎都失败时抛这个，把两边的原始原因都带上（便于排错，不静默）。"""


class LocalEngine:
    """本地引擎：W5 那段 http 直连，原样搬进类里。返回 str。"""

    name = "local"

    def __init__(self, model=None, host=None, timeout=None):
        self.model = model or os.getenv("LOCAL_MODEL", DEFAULT_LOCAL_MODEL)
        self.host = host or os.getenv("LOCAL_HOST", DEFAULT_LOCAL_HOST)
        self.timeout = float(timeout or os.getenv("LOCAL_TIMEOUT", DEFAULT_LOCAL_TIMEOUT))

    def ask(self, prompt, temperature=0.7, max_tokens=800):
        import requests

        # trust_env=False：机房/校园网配了代理时，requests 会把 127.0.0.1 也送去代理。
        session = requests.Session()
        session.trust_env = False
        resp = session.post(
            f"http://{self.host}/api/chat",
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "options": {"temperature": temperature, "num_predict": max_tokens},
                "stream": False,
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()            # 模型名打错返回 404，当场暴露，不返回空答案
        data = resp.json()
        if "error" in data:
            raise LLMError(f"本地服务返回错误：{data['error']}")
        return (data.get("message") or {}).get("content", "").strip()

    def __repr__(self):
        return f"<LocalEngine model={self.model} host={self.host}>"


class APIEngine:
    """云端引擎：客户端按需创建 —— 没配密钥也能纯本地跑（讲义片段 2 的坑）。"""

    name = "api"

    def __init__(self, model=None, base_url=None, timeout=None):
        self.model = model or os.getenv("DEEPSEEK_MODEL", DEFAULT_API_MODEL)
        self.base_url = (base_url or os.getenv("DEEPSEEK_BASE_URL", DEFAULT_API_BASE)).rstrip("/")
        self.timeout = float(timeout or os.getenv("DEEPSEEK_TIMEOUT", DEFAULT_API_TIMEOUT))
        self.client = None                 # 先不建客户端！

    def _ensure_client(self):
        if self.client is not None:
            return self.client
        key = (os.getenv("DEEPSEEK_API_KEY") or "").strip().strip('"').strip("'")
        if not key:
            raise LLMError("未配置 DEEPSEEK_API_KEY（本地引擎仍可用）")
        if any(ord(ch) > 127 for ch in key):
            raise LLMError(
                "DEEPSEEK_API_KEY 含非 ASCII 字符（多半还是 .env.example 的中文占位符），"
                "HTTP 头只能是 ASCII，请换成平台给的真密钥")
        import openai
        self.client = openai.OpenAI(base_url=self.base_url, api_key=key, timeout=self.timeout)
        return self.client

    def ask(self, prompt, temperature=0.7, max_tokens=800):
        client = self._ensure_client()     # 第一次真调用才建客户端
        resp = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (resp.choices[0].message.content or "").strip()

    def __repr__(self):
        return f"<APIEngine model={self.model} base_url={self.base_url}>"


class LLM:
    """统一入口：持有两个引擎，负责选路与双向回退。"""

    def __init__(self, local_model=None):
        self.local = LocalEngine(local_model)
        self.api = APIEngine()
        self.last = {}                     # 最近一次调用的元信息，给测试记录用

    def ask(self, prompt, prefer="local", **kw):
        if prefer not in ("local", "api"):
            raise ValueError('prefer 只能是 "local" 或 "api"')
        first, second = (self.local, self.api) if prefer == "local" else (self.api, self.local)

        started = time.perf_counter()
        try:
            answer = first.ask(prompt, **kw)
        except Exception as exc:           # noqa: BLE001  —— 不吞：先打印，再换另一边
            print(f"[首选引擎失败，自动切换] {first.name} → {second.name}：{exc}")
            try:
                answer = second.ask(prompt, **kw)
            except Exception as exc2:      # noqa: BLE001
                raise LLMError(
                    f"两个引擎都失败：{first.name} -> {exc}；{second.name} -> {exc2}"
                ) from exc2
            self.last = {"engine": second.name, "fallback": True, "prefer": prefer,
                         "seconds": time.perf_counter() - started, "error": str(exc)}
            return answer

        self.last = {"engine": first.name, "fallback": False, "prefer": prefer,
                     "seconds": time.perf_counter() - started, "error": ""}
        return answer

    def __repr__(self):
        return f"<LLM local={self.local.model} api={self.api.model}>"


def ask(prompt, prefer="local", **kw):
    """一句话版本：from llm import ask; ask("…", prefer="api")"""
    return LLM().ask(prompt, prefer=prefer, **kw)


def meta_line(last: dict) -> str:
    """机器可读的一行摘要 —— 边界测试脚本靠它判断「实际走了哪个引擎」。"""
    if not last:
        return "[引擎] - | - | 回退: -"
    return (f"[引擎] {last.get('engine', '-')} | {last.get('seconds', 0):.2f}s | "
            f"回退: {'是' if last.get('fallback') else '否'} | prefer={last.get('prefer', '-')}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="llm.py", description="W6 双引擎：一句问题，两个引擎，prefer 切路")
    parser.add_argument("prompt", nargs="*", help="要问的问题")
    parser.add_argument("--prefer", choices=("local", "api"), default="local",
                        help="先用哪个引擎（另一个作为回退）")
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--max-tokens", type=int, default=800, dest="max_tokens")
    parser.add_argument("--model", default=None, help="覆盖本地模型名，如 qwen3:4b")
    args = parser.parse_args(argv)

    prompt = " ".join(args.prompt).strip()
    if not prompt:
        try:
            prompt = input("问题> ").strip()
        except EOFError:
            print('错误：没有输入问题。用法：python llm.py "你的问题" --prefer local', file=sys.stderr)
            return 2

    llm = LLM(local_model=args.model)
    try:
        answer = llm.ask(prompt, prefer=args.prefer,
                         temperature=args.temperature, max_tokens=args.max_tokens)
    except LLMError as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1

    print(answer)
    print("-" * 62)
    print(meta_line(llm.last))
    return 0


if __name__ == "__main__":
    sys.exit(main())
