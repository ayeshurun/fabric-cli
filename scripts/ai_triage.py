#!/usr/bin/env python3
"""AI Issue Triage Agent for Microsoft Fabric CLI.

Reads issue details, discovers relevant source code, and produces
a high-quality triage assessment backed by codebase evidence,
official docs, and industry standards (RFCs, PEPs).
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import requests
import yaml

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MODEL = os.environ.get("AI_TRIAGE_MODEL", "openai/gpt-4.1")
MAX_TOKENS = int(os.environ.get("AI_TRIAGE_MAX_TOKENS", "1500"))
API_URL = "https://models.inference.ai.azure.com/chat/completions"

# Files always included — they define the CLI's public surface
CORE_FILES = [
    "src/fabric_cli/parsers/fab_global_params.py",
    "src/fabric_cli/parsers/fab_fs_parser.py",
    "src/fabric_cli/parsers/fab_auth_parser.py",
    "src/fabric_cli/core/fab_types.py",
    "src/fabric_cli/core/fab_constant.py",
]

MAX_FILE_CHARS = 4000  # per file
MAX_TOTAL_CODE_CHARS = 30000  # total budget
MAX_DISCOVERED_FILES = 8

# ---------------------------------------------------------------------------
# Issue helpers
# ---------------------------------------------------------------------------

def get_issue_details() -> dict:
    return {
        "number": os.environ.get("ISSUE_NUMBER", ""),
        "title": os.environ.get("ISSUE_TITLE", ""),
        "body": os.environ.get("ISSUE_BODY", ""),
        "labels": os.environ.get("ISSUE_LABELS", ""),
        "author": os.environ.get("ISSUE_AUTHOR", ""),
    }


def determine_prompt_name(labels: str) -> str:
    low = labels.lower()
    if "bug" in low:
        return "bug-triage"
    if "enhancement" in low:
        return "feature-triage"
    return "question-triage"


# ---------------------------------------------------------------------------
# Code discovery
# ---------------------------------------------------------------------------

# Noise words that match too many files
_STOP_WORDS = frozenset({
    "the", "and", "for", "that", "this", "with", "from", "not", "but",
    "are", "was", "were", "have", "has", "been", "will", "can", "should",
    "using", "use", "when", "how", "what", "which", "where", "who",
    "does", "issue", "bug", "error", "feature", "request", "please",
    "expected", "actual", "behavior", "version", "python", "windows",
    "linux", "macos", "darwin", "cli", "fab", "fabric", "microsoft",
    "steps", "reproduce", "description", "additional", "context",
    "possible", "solution", "mode", "interactive", "command", "line",
})


def extract_keywords(text: str) -> list[str]:
    """Extract meaningful keywords from issue text for code search."""
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[#*`\[\](){}]", " ", text)

    words: set[str] = set()
    for raw in text.split():
        w = raw.strip(".,;:!?\"'").lower()
        if len(w) < 3 or w in _STOP_WORDS:
            continue
        # Keep identifiers, flags, CLI-related terms
        if (
            "_" in w
            or w.startswith("-")
            or any(c.isupper() for c in raw[1:])
            or w in {
                "import", "export", "auth", "login", "logout", "environment",
                "notebook", "lakehouse", "warehouse", "pipeline", "workspace",
                "capacity", "gateway", "domain", "connection", "shortcut",
                "semantic", "model", "table", "onelake", "acl", "config",
                "spark", "compute", "certificate", "federated", "token",
                "folder", "item", "cache", "schedule", "jobs", "start",
                "stop", "assign", "unassign", "label", "query",
            }
        ):
            words.add(w.lstrip("-"))

    return list(words)[:20]


def find_relevant_files(keywords: list[str], repo_root: str) -> list[str]:
    """Grep the source tree for files matching issue keywords."""
    src_dir = os.path.join(repo_root, "src/fabric_cli")
    if not os.path.isdir(src_dir):
        return []

    hits: dict[str, int] = {}  # filepath → hit count
    for kw in keywords:
        if len(kw) < 3:
            continue
        try:
            result = subprocess.run(
                ["grep", "-rli", "--include=*.py", kw, src_dir],
                capture_output=True, text=True, timeout=5,
            )
            for f in result.stdout.strip().split("\n"):
                if f:
                    rel = os.path.relpath(f, repo_root)
                    hits[rel] = hits.get(rel, 0) + 1
        except Exception:
            continue

    # Sort by relevance (most keyword hits first)
    ranked = sorted(hits.items(), key=lambda x: -x[1])
    return [f for f, _ in ranked[:MAX_DISCOVERED_FILES]]


def read_code_files(file_paths: list[str], repo_root: str) -> dict[str, str]:
    """Read source files, respecting per-file and total size limits."""
    contents: dict[str, str] = {}
    total = 0
    for f in file_paths:
        full = os.path.join(repo_root, f)
        try:
            text = Path(full).read_text(encoding="utf-8")
        except Exception:
            continue
        if len(text) > MAX_FILE_CHARS:
            text = text[:MAX_FILE_CHARS] + "\n# ... (truncated)"
        if total + len(text) > MAX_TOTAL_CODE_CHARS:
            break
        contents[f] = text
        total += len(text)
    return contents


def format_code_context(code_files: dict[str, str]) -> str:
    if not code_files:
        return ""
    parts = []
    for fp, content in code_files.items():
        parts.append(f"### {fp}\n```python\n{content}\n```")
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

CODE_CONTEXT_PREAMBLE = (
    "## Codebase Reference (source code)\n\n"
    "The following is the **actual source code** of the CLI. "
    "Use it as the authoritative reference for commands, flags, item types, "
    "parsers, constants, and internal logic. "
    "Base your analysis on this real implementation — do not guess.\n\n"
)

STANDARDS_INSTRUCTION = (
    "\n## Standards & best practices\n\n"
    "When relevant, reference established standards and best practices:\n"
    "- **Python**: PEP 8 (style), PEP 257 (docstrings), PEP 484 (type hints)\n"
    "- **CLI conventions**: POSIX Utility Conventions (IEEE Std 1003.1), "
    "GNU Argument Syntax, 12-Factor CLI\n"
    "- **HTTP/REST**: RFC 7231 (HTTP semantics), RFC 7807 (Problem Details), "
    "Microsoft REST API Guidelines\n"
    "- **Auth**: OAuth 2.0 (RFC 6749), MSAL best practices\n"
    "- **General**: semver (for version questions), YAML 1.2 spec\n"
)


def load_prompt(prompt_name: str, repo_root: str) -> dict:
    path = os.path.join(repo_root, f".github/prompts/{prompt_name}.prompt.yml")
    with open(path) as f:
        return yaml.safe_load(f)


def build_messages(
    prompt_data: dict,
    issue: dict,
    code_context: str,
) -> list[dict]:
    """Build the chat messages, injecting code context into the system prompt."""
    messages = []
    for msg in prompt_data.get("messages", []):
        content = msg["content"]

        if msg["role"] == "system":
            # Inject code context + standards before "## Your Task"
            injection = ""
            if code_context:
                injection += CODE_CONTEXT_PREAMBLE + code_context + "\n\n"
            injection += STANDARDS_INSTRUCTION

            marker = "## Your Task"
            if marker in content:
                content = content.replace(marker, injection + marker)
            else:
                content += "\n\n" + injection

        if msg["role"] == "user":
            issue_text = f"**Title:** {issue['title']}\n\n{issue['body']}"
            content = content.replace("{{input}}", issue_text)

        messages.append({"role": msg["role"], "content": content})

    return messages


# ---------------------------------------------------------------------------
# Model call
# ---------------------------------------------------------------------------

def call_model(messages: list[dict], token: str) -> str:
    resp = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": messages,
            "max_tokens": MAX_TOKENS,
        },
        timeout=90,
    )
    if resp.status_code != 200:
        print(f"API error {resp.status_code}: {resp.text[:500]}", file=sys.stderr)
        resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

def parse_assessment(text: str) -> str:
    """Extract assessment category from '### AI Assessment: <category>'."""
    m = re.search(r"###\s*AI Assessment:\s*(.+)", text)
    return m.group(1).strip() if m else "Needs Team Review"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    repo_root = os.environ.get("GITHUB_WORKSPACE", os.getcwd())
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("ERROR: GITHUB_TOKEN not set", file=sys.stderr)
        sys.exit(1)

    issue = get_issue_details()
    prompt_name = determine_prompt_name(issue["labels"])
    print(f"Triaging #{issue['number']}: {issue['title']}")
    print(f"Prompt: {prompt_name}")

    # Discover relevant code
    keywords = extract_keywords(f"{issue['title']} {issue['body']}")
    print(f"Keywords ({len(keywords)}): {keywords[:10]}...")
    discovered = find_relevant_files(keywords, repo_root)

    # Merge core + discovered, deduplicate
    all_files = list(dict.fromkeys(CORE_FILES + discovered))
    code_files = read_code_files(all_files, repo_root)
    print(f"Code context: {len(code_files)} files, ~{sum(len(v) for v in code_files.values())} chars")

    code_context = format_code_context(code_files)

    # Build prompt & call model
    prompt_data = load_prompt(prompt_name, repo_root)
    messages = build_messages(prompt_data, issue, code_context)
    print("Calling model...")
    response_text = call_model(messages, token)

    assessment = parse_assessment(response_text)
    print(f"Assessment: {assessment}")

    # Write outputs for workflow consumption
    output_file = os.environ.get("GITHUB_OUTPUT", "")
    if output_file:
        with open(output_file, "a") as f:
            f.write(f"assessment={assessment}\n")
            f.write(f"prompt_name={prompt_name}\n")
            delim = "EOF_RESPONSE_BODY"
            f.write(f"response<<{delim}\n{response_text}\n{delim}\n")
    else:
        print(f"\n{'='*60}")
        print(f"Assessment: {assessment}")
        print(f"{'='*60}")
        print(response_text)


if __name__ == "__main__":
    main()
