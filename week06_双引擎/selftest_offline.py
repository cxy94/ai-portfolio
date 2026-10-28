# -*- coding: utf-8 -*-
"""selftest_offline.py —— 不联网、不用密钥，验证 llm.py 的双引擎与回退逻辑

跑法：python selftest_offline.py
覆盖：本地/云端两个引擎的请求形态、懒创建客户端、双向回退、不吞异常、命令行元信息。
"""
from __future__ import annotations

import importlib.util
import os
import sys
import types
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

HERE = Path(__file__).resolve().parent
LLM_PATH = HERE / "llm.py"
if not LLM_PATH.exists():
    sys.exit(f"找不到 {LLM_PATH}")

spec = importlib.util.spec_from_file_location("llm", LLM_PATH)
llm = importlib.util.module_from_spec(spec)
sys.modules["llm"] = llm
spec.loader.exec_module(llm)          # type: ignore[union-attr]

PASS, FAIL = [], []


def check(name: str, ok: bool, detail: str = "") -> None:
    (PASS if ok else FAIL).append(name)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f"  -> {detail}" if detail and not ok else ""))


def run_cli(argv):
    out, err = StringIO(), StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            code = llm.main(argv)
    except SystemExit as exc:          # argparse 帮忙时
        code = int(exc.code or 0)
    return code, out.getvalue(), err.getvalue()


# ---------------------------------------------------------------------------
# 1. LocalEngine：请求形态对不对
# ---------------------------------------------------------------------------
class FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status
        self.raise_called = False

    def raise_for_status(self):
        self.raise_called = True
        if self.status_code >= 400:
            raise RuntimeError(f"{self.status_code} Client Error: model not found")

    def json(self):
        return self._payload


captured = {}


class FakeSession:
    def __init__(self):
        self.trust_env = True

    def post(self, url, json=None, timeout=None):
        captured.update(url=url, json=json, timeout=timeout, trust_env=self.trust_env)
        return FakeResponse({"message": {"content": "  把字句是用「把」提前宾语的句式。 "}})


requests_mod = types.ModuleType("requests")
requests_mod.Session = FakeSession
sys.modules["requests"] = requests_mod

engine = llm.LocalEngine(model="qwen2.5:0.5b")
answer = engine.ask("解释把字句", temperature=0.3, max_tokens=120)
check("本地引擎返回 str 且去掉首尾空白", isinstance(answer, str) and answer.startswith("把字句"), repr(answer))
check("本地引擎请求打到 /api/chat", captured["url"].endswith("/api/chat"), captured["url"])
check("本地引擎传了 model / messages / options",
      captured["json"]["model"] == "qwen2.5:0.5b"
      and captured["json"]["messages"][0]["content"] == "解释把字句"
      and captured["json"]["options"] == {"temperature": 0.3, "num_predict": 120},
      str(captured["json"]))
check("本地引擎默认关掉代理（trust_env=False）", captured["trust_env"] is False)
check("本地引擎带了 timeout", captured["timeout"] == engine.timeout)


class FailSession(FakeSession):
    def post(self, *a, **kw):
        return FakeResponse({}, status=404)


requests_mod.Session = FailSession
try:
    llm.LocalEngine().ask("x")
    check("本地 404 会抛错（不返回空答案）", False, "居然没抛")
except Exception as exc:               # noqa: BLE001
    check("本地 404 会抛错（不返回空答案）", "404" in str(exc) or "model not found" in str(exc), str(exc)[:80])
requests_mod.Session = FakeSession


# ---------------------------------------------------------------------------
# 2. APIEngine：客户端按需创建（没密钥也能纯本地跑）
# ---------------------------------------------------------------------------
class FakeCompletions:
    def create(self, **kwargs):
        captured["api"] = kwargs
        return types.SimpleNamespace(
            choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=" 云端答案 "))])


class FakeOpenAI:
    def __init__(self, **kwargs):
        captured["openai_init"] = kwargs
        self.chat = types.SimpleNamespace(completions=FakeCompletions())


openai_mod = types.ModuleType("openai")
openai_mod.OpenAI = FakeOpenAI
sys.modules["openai"] = openai_mod

api = llm.APIEngine()
check("APIEngine 初始化时【不】创建客户端", api.client is None)
os_env_backup = {k: os.environ.get(k) for k in ("DEEPSEEK_API_KEY",)}

os.environ.pop("DEEPSEEK_API_KEY", None)
try:
    api.ask("x")
    check("没配密钥时给出人话错误", False, "居然没抛")
except llm.LLMError as exc:
    check("没配密钥时给出人话错误", "未配置" in str(exc), str(exc)[:80])

os.environ["DEEPSEEK_API_KEY"] = "sk-在这里粘贴你的密钥"
api2 = llm.APIEngine()
try:
    api2.ask("x")
    check("中文占位密钥被拦下（不会变成 UnicodeEncodeError）", False, "居然没抛")
except llm.LLMError as exc:
    check("中文占位密钥被拦下（不会变成 UnicodeEncodeError）", "ASCII" in str(exc), str(exc)[:80])

os.environ["DEEPSEEK_API_KEY"] = "sk-abc123XYZ"
api3 = llm.APIEngine()
out3 = api3.ask("给《愚公移山》出一道题", temperature=0.2, max_tokens=300)
check("配好密钥后能拿到云端答案", out3 == "云端答案", repr(out3))
check("云端请求带 model / messages / 参数",
      captured["api"]["model"] == "deepseek-chat"
      and captured["api"]["messages"][0]["content"] == "给《愚公移山》出一道题"
      and captured["api"]["temperature"] == 0.2 and captured["api"]["max_tokens"] == 300,
      str(captured["api"]))
check("客户端是按需创建的（第一次 ask 后才存在）", api3.client is not None)


# ---------------------------------------------------------------------------
# 3. LLM：三条路径 + 双向回退 + 不吞异常
# ---------------------------------------------------------------------------
def make_llm(local_ok=True, api_ok=True):
    obj = llm.LLM(local_model="qwen2.5:0.5b")

    def local_ask(prompt, **kw):
        if not local_ok:
            raise ConnectionError("HTTPConnectionPool(host='127.0.0.1', port=11434): Connection refused")
        return "本地答案"

    def api_ask(prompt, **kw):
        if not api_ok:
            raise llm.LLMError("未配置 DEEPSEEK_API_KEY（本地引擎仍可用）")
        return "云端答案"

    obj.local.ask = local_ask
    obj.api.ask = api_ask
    return obj


# ① 正常本地
busy = make_llm()
check("① 正常本地：返回本地答案", busy.ask("q", prefer="local") == "本地答案")
check("① 正常本地：meta 显示 local 且未回退",
      busy.last["engine"] == "local" and busy.last["fallback"] is False, str(busy.last))

# ② 本地挂 → 切云端（并打印原因）
out, err = StringIO(), StringIO()
broken_local = make_llm(local_ok=False)
with redirect_stdout(out):
    got = broken_local.ask("q", prefer="local")
printed = out.getvalue()
check("② 本地挂：自动切云端并拿到回答", got == "云端答案")
check("② 本地挂：打印了切换原因（这就是测试证据）",
      "[首选引擎失败，自动切换] local → api" in printed and "Connection refused" in printed, printed[:120])
check("② 本地挂：meta 记录 fallback=是 且带原错误",
      broken_local.last["engine"] == "api" and broken_local.last["fallback"] is True
      and "Connection refused" in broken_local.last["error"], str(broken_local.last))

# ③ 云端挂 → 切本地（双向回退）
out3, _ = StringIO(), StringIO()
broken_api = make_llm(api_ok=False)
with redirect_stdout(out3):
    got3 = broken_api.ask("q", prefer="api")
check("③ prefer=api 但云端不可用：回退到本地", got3 == "本地答案")
check("③ 回退是双向的（打印 api → local）", "api → local" in out3.getvalue(), out3.getvalue()[:100])
check("③ meta 显示走了 local 且回退=是",
      broken_api.last["engine"] == "local" and broken_api.last["fallback"] is True, str(broken_api.last))

# 两边都挂 → 抛 LLMError，带两侧原因，绝不返回空串
both = make_llm(local_ok=False, api_ok=False)
try:
    with redirect_stdout(StringIO()):
        both.ask("q", prefer="local")
    check("两边都挂：抛 LLMError 而不是返回空字符串", False, "居然没抛")
except llm.LLMError as exc:
    msg = str(exc)
    check("两边都挂：抛 LLMError 而不是返回空字符串", True)
    check("两边都挂：错误里带两侧原始原因",
          "Connection refused" in msg and "未配置 DEEPSEEK_API_KEY" in msg, msg[:160])

# 非法 prefer
try:
    busy.ask("q", prefer="cloud")
    check("非法 prefer 会被拒绝", False, "居然没抛")
except ValueError:
    check("非法 prefer 会被拒绝", True)

# meta_line 格式
line = llm.meta_line({"engine": "api", "seconds": 2.63, "fallback": True, "prefer": "local"})
check("meta 行包含引擎/耗时/回退/prefer",
      "api" in line and "2.63s" in line and "回退: 是" in line and "prefer=local" in line, line)


# ---------------------------------------------------------------------------
# 4. 命令行：成功与失败各自的退出码与输出
# ---------------------------------------------------------------------------
orig_local_ask = llm.LocalEngine.ask
orig_api_ask = llm.APIEngine.ask
llm.LocalEngine.ask = lambda self, prompt, **kw: "本地答案"
code, out, err = run_cli(["给《愚公移山》出一道题", "--prefer", "local"])
check("命令行成功退出码为 0", code == 0, f"实际 {code}；err={err[:120]}")
check("命令行打印答案与 [引擎] 摘要行", "本地答案" in out and out.strip().splitlines()[-1].startswith("[引擎] local"), out[-160:])

# 两边都失败：本地抛错、云端也抛错（无密钥）
llm.LocalEngine.ask = lambda self, prompt, **kw: (_ for _ in ()).throw(ConnectionError("refused"))
llm.APIEngine.ask = lambda self, prompt, **kw: (_ for _ in ()).throw(llm.LLMError("未配置 DEEPSEEK_API_KEY"))
code, out, err = run_cli(["测试", "--prefer", "local"])
check("命令行两边都失败时退出码为 1", code == 1, f"实际 {code}");
check("命令行失败时把两侧原因打到 stderr", "两个引擎都失败" in err, err[:160])
llm.LocalEngine.ask = orig_local_ask
llm.APIEngine.ask = orig_api_ask

# 恢复常量
for k, v in os_env_backup.items():
    if v is None:
        os.environ.pop(k, None)
    else:
        os.environ[k] = v

print("\n" + "=" * 62)
print(f"通过 {len(PASS)} 项，失败 {len(FAIL)} 项")
if FAIL:
    print("失败项：" + "；".join(FAIL))
    sys.exit(1)
print("离线自检通过：懒创建客户端、双向回退、切换日志、不吞异常、命令行元信息，全部符合讲义要求。")
