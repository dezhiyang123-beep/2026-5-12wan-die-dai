"""
Stop Hook: 每轮对话结束时，从transcript中提取记忆
检查本轮是否有：用户否决、用户修正、步骤完成、新偏好表达
"""

import json
import sys
import os
import io
from datetime import datetime

# Windows环境强制UTF-8
if sys.platform == "win32":
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

PROJECT_DIR = os.environ.get("CLAUDE_PROJECT_DIR", os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
CLIENTS_DIR = os.path.join(PROJECT_DIR, ".claude", "clients")

def get_hook_input():
    try:
        data = json.load(sys.stdin)
        return data
    except:
        return {}

def find_active_client():
    """查找当前活跃的客户"""
    if not os.path.exists(CLIENTS_DIR):
        return None
    latest_time = 0
    latest_client = None
    for name in os.listdir(CLIENTS_DIR):
        client_dir = os.path.join(CLIENTS_DIR, name)
        if os.path.isdir(client_dir):
            mtime = os.path.getmtime(client_dir)
            if mtime > latest_time:
                latest_time = mtime
                latest_client = name
    return latest_client

def read_recent_transcript(transcript_path, max_lines=100):
    """读取最近的transcript记录"""
    if not transcript_path or not os.path.exists(transcript_path):
        return []

    try:
        with open(transcript_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # 取最后max_lines行
            return lines[-max_lines:]
    except:
        return []

def extract_step_completions(transcript_lines):
    """从transcript中提取步骤完成信号"""
    completions = []
    for line in transcript_lines:
        try:
            entry = json.loads(line.strip())
            if entry.get("type") == "assistant":
                content = str(entry.get("message", {}).get("content", ""))
                # 检测步骤完成标记
                for step_num in range(11):
                    step_str = f"Step {step_num:02d}"
                    alt_str = f"Step {step_num}"
                    if (step_str in content or alt_str in content) and ("完成" in content or "进入" in content):
                        completions.append(f"Step {step_num:02d}")
        except:
            continue
    return list(set(completions))

def update_project_progress(client_name, completions):
    """更新项目进度记录"""
    if not completions or not client_name:
        return

    progress_file = os.path.join(CLIENTS_DIR, client_name, "session_progress.yaml")
    os.makedirs(os.path.dirname(progress_file), exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    with open(progress_file, "a", encoding="utf-8") as f:
        for step in completions:
            f.write(f"  - step: \"{step}\"\n    completed_at: \"{timestamp}\"\n\n")

def main():
    hook_input = get_hook_input()
    transcript_path = hook_input.get("transcript_path", "")

    client = find_active_client()

    # 从transcript提取步骤完成信号
    if transcript_path:
        transcript_lines = read_recent_transcript(transcript_path, 50)
        completions = extract_step_completions(transcript_lines)

        if completions and client:
            update_project_progress(client, completions)

    # Stop hook的stdout不会注入Claude上下文（只有SessionStart和UserPromptSubmit会）
    # 所以这里不输出到stdout，只做后台记录
    sys.exit(0)

if __name__ == "__main__":
    main()
