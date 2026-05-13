"""
SessionStart Hook: 新对话开始时加载所有相关记忆
输出到stdout → 注入Claude上下文，让Claude带着记忆开始工作
"""

import json
import sys
import os
import io
import glob

# Windows环境强制UTF-8
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MEMORY_USER = os.path.join(PROJECT_DIR, ".claude", "memory", "user", "preferences.yaml")
CLIENTS_DIR = os.path.join(PROJECT_DIR, ".claude", "clients")

def read_yaml_raw(filepath):
    """读取YAML文件的原始文本（不解析，避免依赖pyyaml）"""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return None

def read_file_safe(filepath, max_lines=50):
    """安全读取文件，限制行数"""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()[:max_lines]
            return "".join(lines)
    except:
        return None

def find_all_clients():
    """列出所有客户文件夹"""
    if not os.path.exists(CLIENTS_DIR):
        return []
    clients = []
    for name in os.listdir(CLIENTS_DIR):
        if os.path.isdir(os.path.join(CLIENTS_DIR, name)):
            clients.append(name)
    return clients

def load_client_memory(client_name):
    """加载一个客户的所有记忆"""
    client_dir = os.path.join(CLIENTS_DIR, client_name)
    memory = {"name": client_name, "sections": []}

    # 品牌语法（取前30行摘要）
    bg = read_file_safe(os.path.join(client_dir, "brand_grammar.yaml"), 30)
    if bg:
        memory["sections"].append(("品牌语法", bg))

    # 偏好
    pref = read_file_safe(os.path.join(client_dir, "preferences.yaml"), 20)
    if pref:
        memory["sections"].append(("偏好", pref))

    # 即时记忆（对话中捕获的）
    live = read_file_safe(os.path.join(client_dir, "live_memory.yaml"), 30)
    if live:
        memory["sections"].append(("即时记忆（对话中捕获）", live))

    # 项目历史（取最近的）
    ph = read_file_safe(os.path.join(client_dir, "project_history.yaml"), 30)
    if ph:
        memory["sections"].append(("项目历史", ph))

    return memory

def main():
    output = []
    output.append("=" * 60)
    output.append("[记忆系统] 会话启动 — 加载记忆中...")
    output.append("=" * 60)

    # 1. 用户层记忆
    user_mem = read_file_safe(MEMORY_USER, 30)
    if user_mem:
        output.append("\n## 用户偏好（跨所有项目）")
        output.append(user_mem)
    else:
        output.append("\n## 用户偏好：无历史记录")

    # 2. 客户层记忆
    clients = find_all_clients()
    if clients:
        output.append(f"\n## 已有客户记忆：{', '.join(clients)}")
        for client in clients:
            mem = load_client_memory(client)
            if mem["sections"]:
                output.append(f"\n### {client}")
                for section_name, content in mem["sections"]:
                    output.append(f"\n**{section_name}**:")
                    # 截取关键行，不超过10行
                    lines = content.strip().split("\n")[:10]
                    output.append("\n".join(lines))
                    if len(content.strip().split("\n")) > 10:
                        output.append("  ... (更多内容请读取原文件)")
    else:
        output.append("\n## 客户记忆：无历史客户")

    output.append("\n" + "=" * 60)
    output.append("[记忆系统] 加载完成。以上记忆将影响本次对话的所有设计决策。")
    output.append("=" * 60)

    # 输出到stdout → 注入Claude上下文
    print("\n".join(output))
    sys.exit(0)

if __name__ == "__main__":
    main()
