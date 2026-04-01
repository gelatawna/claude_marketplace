#!/usr/bin/env python3
"""Update session file from conversation transcript on session end.

Reads the transcript JSONL from stdin (hook input), finds the active session
file, and updates it with context from the conversation.

This is a simplified version that extracts key information without LLM calls.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=check)


def get_changed_files(repo_name: str) -> list[str]:
    result = git("diff", "--name-only", check=False)
    files = result.stdout.strip().splitlines()
    return [f"{repo_name}/{f}" for f in files if f]


def extract_user_messages(transcript_path: str) -> list[str]:
    """Extract user messages from the transcript JSONL."""
    messages = []
    try:
        with open(transcript_path) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("type") == "human" or entry.get("role") == "user":
                        content = entry.get("content", "")
                        if isinstance(content, str) and content.strip():
                            messages.append(content.strip())
                        elif isinstance(content, list):
                            for block in content:
                                if isinstance(block, dict) and block.get("type") == "text":
                                    text = block.get("text", "").strip()
                                    if text:
                                        messages.append(text)
                except json.JSONDecodeError:
                    continue
    except (FileNotFoundError, PermissionError):
        pass
    return messages


def extract_tool_uses(transcript_path: str) -> list[str]:
    """Extract file-modifying tool uses from transcript."""
    tools = []
    try:
        with open(transcript_path) as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    if entry.get("type") == "tool_use" or entry.get("type") == "tool_result":
                        tool_name = entry.get("name", "")
                        tool_input = entry.get("input", {})
                        if tool_name in ("Write", "Edit", "MultiEdit") and "file_path" in tool_input:
                            tools.append(f"{tool_name}: {tool_input['file_path']}")
                        elif tool_name == "Bash" and "command" in tool_input:
                            cmd = tool_input["command"][:100]
                            tools.append(f"Bash: {cmd}")
                except json.JSONDecodeError:
                    continue
    except (FileNotFoundError, PermissionError):
        pass
    return tools


def main() -> None:
    # Read hook input from stdin
    try:
        hook_input = json.loads(sys.stdin.read())
    except (json.JSONDecodeError, EOFError):
        hook_input = {}

    transcript_path = hook_input.get("transcript_path", "")

    branch = git("branch", "--show-current", check=False).stdout.strip()
    if not branch:
        return

    remote_url = git("remote", "get-url", "origin", check=False).stdout.strip()
    repo_name = Path(remote_url).name.removesuffix(".git") if remote_url else "unknown"

    session_dir = Path.cwd() / ".claude" / "sessions" / branch
    if not session_dir.is_dir():
        return

    session_files = sorted(session_dir.glob("session-*.md"))
    if not session_files:
        return

    latest = session_files[-1]
    content = latest.read_text()

    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    # Update ended_at in frontmatter
    content = re.sub(r"ended_at:\s*null", f"ended_at: {now}", content)

    # Collect updates
    changed_files = get_changed_files(repo_name)
    user_messages = extract_user_messages(transcript_path) if transcript_path else []
    tool_uses = extract_tool_uses(transcript_path) if transcript_path else []

    # Build a conversation summary for Working Memory
    conversation_notes = []
    if user_messages:
        conversation_notes.append("Topics discussed this session:")
        for msg in user_messages[:10]:  # Cap at 10 messages
            short = msg[:150].replace("\n", " ")
            conversation_notes.append(f"  - {short}")

    # Update Files Changed section
    if changed_files:
        files_section = "## Files Changed\n\n" + "\n".join(f"- {f}" for f in changed_files)
        content = re.sub(
            r"## Files Changed.*?(?=\n## |\Z)",
            files_section + "\n",
            content,
            flags=re.DOTALL,
        )

    # Append conversation notes to Working Memory if we have them
    if conversation_notes:
        notes_text = "\n".join(conversation_notes)
        # Find Working Memory section and append
        wm_pattern = r"(### Working Memory\n)"
        if re.search(wm_pattern, content):
            content = re.sub(
                wm_pattern,
                f"\\1- Session ended: {now}\n- {notes_text}\n",
                content,
            )

    latest.write_text(content)


if __name__ == "__main__":
    main()
