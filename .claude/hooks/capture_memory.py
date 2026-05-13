"""
UserPromptSubmit Hook: 对话中即时捕获记忆信号
每次用户发送消息时自动运行，检测偏好/否定/修正信号，写入对应记忆文件
"""

import json
import sys
import os
import re
import io
from datetime import datetime

# Windows环境强制UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 项目根目录
PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MEMORY_USER = os.path.join(PROJECT_DIR, ".claude", "memory", "user", "preferences.yaml")
CLIENTS_DIR = os.path.join(PROJECT_DIR, ".claude", "clients")

# 读取stdin获取hook数据
def get_hook_input():
    try:
        # Windows环境下强制UTF-8读取stdin
        if sys.platform == "win32":
            import io
            sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
        data = json.load(sys.stdin)
        return data
    except:
        return {}

# 信号检测规则
NEGATIVE_SIGNALS = [
    r"太(保守|激进|像|简单|复杂|丑|廉价|高端|圆润|方正)",
    r"不(要|能|行|对|好|像|够|满意|接受)",
    r"别(做|搞|用|加|改)",
    r"禁止",
    r"换(一|张|个|掉)",
    r"重新(找|做|来|生成|设计)",
    r"这(张|个|款)(不对|不行|不好|太)",
    r"删(掉|除|了)",
]

POSITIVE_SIGNALS = [
    r"(这个|这款|这张)(好|对|可以|不错|很好|棒)",
    r"就(这样|这个|按这个)",
    r"(对|是|没错|正确|同意)",
    r"继续(这个|按这个)",
    r"保(留|持)(这个|这种)",
]

USER_HABIT_SIGNALS = [
    r"(以后|每次|总是|永远|都要|一直)",
    r"我(喜欢|习惯|偏好|想要|需要)",
    r"(不要|别)(再|总是|每次)",
]

CLIENT_FACT_SIGNALS = [
    r"(这个|这家)客户(喜欢|讨厌|要求|偏好|说|反馈)",
    r"客户(说|要|不要|反馈)",
    r"品牌(调性|风格|偏好|红线)",
]

def detect_signals(prompt):
    """检测用户prompt中的记忆信号"""
    signals = []

    for pattern in NEGATIVE_SIGNALS:
        if re.search(pattern, prompt):
            signals.append({"type": "negative", "pattern": pattern, "text": prompt[:200]})
            break

    for pattern in POSITIVE_SIGNALS:
        if re.search(pattern, prompt):
            signals.append({"type": "positive", "pattern": pattern, "text": prompt[:200]})
            break

    for pattern in USER_HABIT_SIGNALS:
        if re.search(pattern, prompt):
            signals.append({"type": "user_habit", "pattern": pattern, "text": prompt[:200]})
            break

    for pattern in CLIENT_FACT_SIGNALS:
        if re.search(pattern, prompt):
            signals.append({"type": "client_fact", "pattern": pattern, "text": prompt[:200]})
            break

    return signals

def append_to_yaml(filepath, entry):
    """追加记忆条目到YAML文件"""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    line = f"  - signal: \"{entry['text'][:100]}\"\n    captured_at: \"{timestamp}\"\n    type: \"{entry['type']}\"\n\n"

    # 如果文件不存在，创建头部
    if not os.path.exists(filepath):
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(f"# 自动捕获的记忆信号\nlast_updated: \"{timestamp}\"\n\nsignals:\n")

    # 追加条目
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(line)

def find_active_client():
    """查找当前活跃的客户（最近修改的客户文件夹）"""
    if not os.path.exists(CLIENTS_DIR):
        return None

    latest_time = 0
    latest_client = None

    for name in os.listdir(CLIENTS_DIR):
        client_dir = os.path.join(CLIENTS_DIR, name)
        if os.path.isdir(client_dir) and name != "README.md":
            mtime = os.path.getmtime(client_dir)
            if mtime > latest_time:
                latest_time = mtime
                latest_client = name

    return latest_client

def main():
    hook_input = get_hook_input()
    prompt = hook_input.get("prompt", "")

    if not prompt or len(prompt) < 3:
        sys.exit(0)

    signals = detect_signals(prompt)

    if not signals:
        sys.exit(0)

    output_messages = []

    for signal in signals:
        if signal["type"] == "user_habit":
            # 写入用户层记忆
            append_to_yaml(MEMORY_USER, signal)
            output_messages.append(f"[记忆] 用户偏好已记录: {signal['text'][:60]}")

        elif signal["type"] in ("negative", "positive", "client_fact"):
            # 写入客户层记忆
            client = find_active_client()
            if client:
                client_memory = os.path.join(CLIENTS_DIR, client, "live_memory.yaml")
                append_to_yaml(client_memory, signal)
                output_messages.append(f"[记忆] 客户信号已记录({client}): {signal['text'][:60]}")
            else:
                # 没有活跃客户，写入用户层
                append_to_yaml(MEMORY_USER, signal)
                output_messages.append(f"[记忆] 信号已记录(用户层): {signal['text'][:60]}")

    # 输出到stdout → 注入Claude上下文
    if output_messages:
        print("\n".join(output_messages))

    sys.exit(0)

if __name__ == "__main__":
    main()
