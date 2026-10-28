#!/usr/bin/env bash
# W6 · 三条路径边界测试，自动生成 week06_test_log.md（Windows / Git Bash）
#
# 用法：
#   bash test_paths.sh                      # 默认：用“空端口”模拟本地不可用（不打断你的 Ollama）
#   bash test_paths.sh --stop-ollama        # 真把 Ollama 关掉再测（讲义原话做法），末尾给出重启命令
#   bash test_paths.sh --no-cloud           # 只测本地两条（没密钥/不想花钱时）
#   Q="换一个问题" bash test_paths.sh        # 换测试问题
#   OUT=../week06_test_log.md bash test_paths.sh
#
# 它替你做四件事：跑三条路径 → 抓 [引擎] 摘要与回退日志原文 → 写 markdown 表 → 提示你补“质量点评”
set -uo pipefail

# Windows 上 Python 默认按 GBK 输出，而本脚本里的中文匹配串是 UTF-8 → 强行统一成 UTF-8，
# 否则 [引擎] 摘要抓不到、写进 md 的记录全成乱码。
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
PY="${PY:-python}"
Q="${Q:-给《愚公移山》出一道 HSK4 阅读题，只要题干和四个选项}"
OUT="${OUT:-$DIR/week06_test_log.md}"
MODEL="${LOCAL_MODEL:-qwen2.5:0.5b}"
HOST="${LOCAL_HOST:-127.0.0.1:11434}"
DEAD_HOST="127.0.0.1:11499"        # 没人监听的端口，用来模拟“本地引擎不可用”
BASE="http://${HOST}"
MODE="simulate"
DO_CLOUD=1

for arg in "$@"; do
  case "$arg" in
    --stop-ollama) MODE="stop" ;;
    --no-cloud)    DO_CLOUD=0 ;;
    -h|--help)     sed -n '2,12p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *)             echo "未知参数：$arg（用 --help 看用法）"; exit 2 ;;
  esac
done

say()  { printf '%s\n' "$*"; }
fail() { printf '[FAIL] %s\n' "$*"; }

say "== W6 边界测试（$(uname -s)，模式：$([ "$MODE" = stop ] && echo 真关-ollama || echo simulate)）=="
say "问题：$Q"
say

# ---------- 预检 ----------
command -v "$PY" >/dev/null 2>&1 || { fail "找不到 python（试试 PY=/d/Python311/python.exe bash test_paths.sh）"; exit 1; }
[ -f "$DIR/llm.py" ] || { fail "找不到 $DIR/llm.py"; exit 1; }

local_up=0
if curl -sS --noproxy '*' --max-time 3 "$BASE/api/version" >/dev/null 2>&1; then
  local_up=1
  say "本地服务 $BASE：在跑"
else
  say "本地服务 $BASE：连不上（第1组会跳过；先装/启动 Ollama）"
fi
KEY_OK=0
if [ -n "${DEEPSEEK_API_KEY:-}" ]; then
  KEY_OK=1
  say "云端密钥：环境变量里已设置"
elif [ -f "$ROOT/.env" ] && grep -qE '^[[:space:]]*DEEPSEEK_API_KEY=.+' "$ROOT/.env"; then
  KEY_OK=1
  say "云端密钥：$ROOT/.env 里已填写"
else
  say "云端密钥：没有可用密钥 → 第②组测不了回退、第③组会自动回退到本地"
fi
say

ROWS=""
LOGS=""

# ---------- 跑一组 ----------
trim46() {   # 按字符截断（cut -c 按字节，会把中文切半个）
  PYTHONUTF8=1 python -c 'import sys; s=" ".join(sys.stdin.read().split()); print(s[:46])'
}

run_case() {
  local no="$1" cond="$2"
  shift 2
  local raw code meta engine detail answer verdict

  raw="$(env "$@" 2>&1)"
  code=$?

  meta="$(printf '%s\n' "$raw" | sed -n 's/^\[引擎\] /&/p' | tail -n 1)"
  engine="$(printf '%s\n' "$meta" | sed -n 's/^\[引擎\] \([^ ]*\) |.*/\1/p')"
  detail="$(printf '%s\n' "$meta" | sed 's/^\[引擎\] //; s/ | / ／ /g')"

  # 答案摘录：优先取第一行“不是日志”的内容
  answer="$(printf '%s\n' "$raw" | grep -v '^\[首选引擎失败' | grep -v '^\[引擎\]' | grep -v '^-*$' | head -n 1 | trim46)"

  if [ "$code" -ne 0 ]; then
    verdict="待你判断：配置问题还是网络问题？"
    [ -z "$detail" ] && detail="两边都失败（退出码 $code）"
  else
    verdict="待你点评（示例：符合预期）"
  fi

  printf '  第%s组 %s → %s\n' "$no" "$cond" "${detail:-（无输出）}"

  if printf '%s\n' "$raw" | grep -q '^\[首选引擎失败，自动切换\]'; then
    LOGS="${LOGS}
### 第 ${no} 组｜${cond}

\`\`\`text
$(printf '%s\n' "$raw" | grep -E '^\[首选引擎失败，自动切换\]')
\`\`\`
"
  fi

  ROWS="${ROWS}| ${no} | ${cond} | ${engine:-—} | ${detail:-—} | ${answer:-（空）} | ${verdict} |
"
}

# ① 正常本地（必须在关 Ollama 之前跑）
if [ "$local_up" = 1 ]; then
  run_case 1 "Ollama 开，prefer=\"local\"" "$PY" "$DIR/llm.py" "$Q" --prefer local
else
  ROWS="${ROWS}| 1 | Ollama 未运行，prefer=\"local\" | — | （跳过） | — | 先启动 Ollama 再跑 |
"
  say "  第1组 跳过：本地服务没起来"
fi

# ---------- 真关 Ollama（可选，只在第1组之后） ----------
if [ "$MODE" = "stop" ]; then
  say
  say "== 关闭 Ollama（讲义第 4 步的做法） =="
  taskkill //F //IM "ollama app.exe" >/dev/null 2>&1 || true
  taskkill //F //IM "ollama.exe"     >/dev/null 2>&1 || true
  sleep 2
  if curl -sS --noproxy '*' --max-time 2 "$BASE/api/version" >/dev/null 2>&1; then
    fail "关不掉（端口可能被别的进程占着）——改用默认的 simulate 模式重跑"
    exit 1
  fi
  say "已关闭。"
  say
fi

# ② 本地不可用 → 应自动切云端
if [ "$KEY_OK" = 0 ]; then
  ROWS="${ROWS}| 2 | 本地不可用，prefer=\"local\" | — | （未测：缺云端密钥） | — | 先配 .env 再重跑 |
"
  say "  第2组 跳过：没有云端密钥，回退无处可去"
elif [ "$MODE" = "stop" ]; then
  run_case 2 "Ollama 已关闭，prefer=\"local\"（真关服务）" "$PY" "$DIR/llm.py" "$Q" --prefer local
else
  run_case 2 "本地不可用（LOCAL_HOST 指向空端口 ${DEAD_HOST}），prefer=\"local\"" \
    LOCAL_HOST="$DEAD_HOST" "$PY" "$DIR/llm.py" "$Q" --prefer local
fi

# ③ prefer="api"
if [ "$DO_CLOUD" = 1 ]; then
  if [ "$KEY_OK" = 1 ]; then
    run_case 3 "prefer=\"api\"" "$PY" "$DIR/llm.py" "$Q" --prefer api
  else
    run_case 3 "prefer=\"api\"（没配密钥 → 应优雅回退本地）" "$PY" "$DIR/llm.py" "$Q" --prefer api
  fi
else
  ROWS="${ROWS}| 3 | prefer=\"api\"（--no-cloud 跳过） | — | （未测） | — | 课后补 |
"
fi

# ---------- 写 markdown ----------
{
  printf '# W6 双引擎边界测试记录\n\n'
  printf -- '- 生成时间：%s\n' "$(date '+%Y-%m-%d %H:%M:%S')"
  printf -- '- 环境：%s　Python：%s\n' "$(uname -s)" "$("$PY" -c 'import sys;print(sys.version.split()[0])')"
  printf -- '- 本地模型：%s　本地地址：%s\n' "$MODEL" "$HOST"
  printf -- '- 测试问题：%s\n' "$Q"
  if [ "$MODE" = "stop" ]; then
    printf -- '- 第2组做法：**真关掉 Ollama 服务**（讲义第 4 步原话）\n'
  else
    printf -- '- 第2组做法：把 `LOCAL_HOST` 指向空端口 `%s`，模拟「本地引擎不可用」；\n' "$DEAD_HOST"
    printf -- '  效果与关掉 Ollama 相同（都是 ConnectionError），但不打断你正在用的服务。\n'
    printf -- '  想严格按讲义做：`bash test_paths.sh --stop-ollama`\n'
  fi
  printf '\n## 一、三条路径\n\n'
  printf '| # | 测试条件 | 实际走的引擎 | 耗时／回退 | 答案摘录 | 是否符合预期／怎么改的 |\n'
  printf '|---|---|---|---|---|---|\n'
  printf '%s' "$ROWS"
  printf '\n## 二、回退日志原文（最关键的证据，别只写“成功了”）\n'
  if [ -n "$LOGS" ]; then
    printf '%s' "$LOGS"
  else
    printf '\n（本次没有触发回退——若第 2 组也没打印切换行，说明本地其实还活着，检查 LOCAL_HOST 设置。）\n'
  fi
  printf '\n## 三、质量点评（自己写，不许空着）\n\n'
  printf '1. 同一个问题，本地与云端的答案差在哪？各抄一句原话对比：\n\n'
  printf '2. 本地速度 vs 云端速度（看上面的耗时）：\n\n'
  printf '3. 这套封装对你的课堂意味着什么？哪类任务你会固定 `prefer="local"`，哪类固定 `"api"`：\n\n'
} > "$OUT"

say
say "== 已生成：$OUT =="
say "   打开它，把「是否符合预期」和「质量点评」补完，再 push。"

if [ "$MODE" = "stop" ]; then
  cat <<'EOF'

== 别忘了把 Ollama 起回来 ==
   方式一（推荐）：开始菜单搜 Ollama 重新打开
   方式二：Git Bash 里跑  "$LOCALAPPDATA/Programs/Ollama/ollama app.exe" &
   验证：curl -sS --noproxy '*' http://127.0.0.1:11434/api/version
EOF
fi
