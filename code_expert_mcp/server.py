#!/usr/bin/env python3
"""
code-expert MCP Server (MiniMax 版)

直接调 MiniMax API，不依赖 OpenClaw。
通过 MCP stdio 暴露给 Claude Desktop / Cursor 等 MCP 客户端。

环境变量：
  MINIMAX_API_KEY   — MiniMax API Key（必填）
  MINIMAX_MODEL     — 模型名，默认 MiniMax-M3
"""

import json
import subprocess
import sys
import os
import urllib.request
import urllib.error

# ─── 配置 ──────────────────────────────────────────────────────────────
MINIMAX_API_KEY = os.environ.get("MINIMAX_API_KEY", "")
MINIMAX_MODEL   = os.environ.get("MINIMAX_MODEL", "MiniMax-M3")
MINIMAX_BASE_URL = "https://api.minimaxi.com/anthropic/v1"

PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME      = "code-expert"
SERVER_VERSION   = "1.0.0"


# ─── MiniMax API 调用 ──────────────────────────────────────────────────
def call_minimax(system: str, user_message: str, timeout: int = 120) -> str:
    """调 MiniMax Anthropic 兼容接口，返回文本。"""
    if not MINIMAX_API_KEY:
        return "[Error] MINIMAX_API_KEY 环境变量未设置"

    payload = {
        "model": MINIMAX_MODEL,
        "max_tokens": 8192,
        "system": system,
        "messages": [
            {"role": "user", "content": user_message}
        ]
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{MINIMAX_BASE_URL}/messages",
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "x-api-key": MINIMAX_API_KEY,
            "anthropic-version": "2023-06-01",
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.load(resp)
            # 解析 Anthropic 格式响应（处理 text + thinking 两种 block）
            if "content" in result:
                parts = []
                for block in result["content"]:
                    if block.get("type") == "thinking":
                        parts.append(f"[思考过程]\n{block.get('thinking', '')}")
                    elif block.get("type") == "text":
                        parts.append(block["text"])
                if parts:
                    return "\n\n".join(parts)
            return json.dumps(result, ensure_ascii=False)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return f"[HTTP {e.code}] {body[:500]}"
    except Exception as e:
        return f"[Error] {e}"


# ─── System Prompt ────────────────────────────────────────────────────
CODE_EXPERT_SYSTEM = """你是一个专业的代码编写专家 Agent，专注于代码全生命周期质量。

你的核心能力：
- 代码编写与重构（JS/TS/Python/Go/Java/Rust/C++）
- 代码审查：🔴严重→🟠高级→🟡中级→🔵低级 四级问题分级
- 安全审计：注入漏洞、硬编码密钥、认证绕过、OWASP Top 10
- 性能优化：N+1查询、缺失索引、同步阻塞、算法优化、缓存策略
- 数据库设计：表设计规范、索引优化、ORM最佳实践
- API安全：REST/GraphQL/WebSocket安全规范
- 架构评审：设计模式、微服务拆分、CQRS/Saga、模块化解耦
- 调试诊断：四步调试法（复现→定位→修复→验证）
- 依赖审计：CVE扫描、SBOM、许可证合规

输出风格：
- 严谨务实，数据驱动，简洁直接
- 代码示例精确到行，标注语言版本
- 审查报告用 Markdown 表格
- 行动项明确标注优先级（🔴🟠🟡🔵）

审查维度：安全漏洞 > 代码质量 > 性能问题 > 规范遵从 > 架构建议"""


# ─── MCP 工具定义 ────────────────────────────────────────────────────
TOOLS = [
    {
        "name": "code_review",
        "description": "对代码片段或代码仓库路径进行全面的代码审查。涵盖：安全漏洞、代码质量、性能问题、规范遵从、依赖审计、架构建议。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code":      {"type": "string", "description": "要审查的代码内容（优先使用）"},
                "language":  {"type": "string", "description": "代码语言，如 typescript、python、go、java"},
                "repo_path": {"type": "string", "description": "本地代码仓库路径（服务器上）"},
                "repo_url":  {"type": "string", "description": "Git 仓库 URL（自动 clone 后审查）"},
                "focus": {
                    "type": "string",
                    "enum": ["all", "security", "performance", "quality", "architecture"],
                    "default": "all",
                    "description": "审查重点方向",
                },
            },
        },
    },
    {
        "name": "code_audit",
        "description": "对项目进行深度的安全+质量审计，包括 CVE 扫描、依赖分析、配置检查。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {"type": "string", "description": "本地代码仓库路径"},
                "repo_url":  {"type": "string", "description": "Git 仓库 URL"},
                "level": {
                    "type": "string",
                    "enum": ["fast", "full"],
                    "default": "fast",
                    "description": "审计深度",
                },
            },
        },
    },
    {
        "name": "generate_code",
        "description": "根据自然语言需求生成高质量代码。支持 JS/TS/Python/Go/Java/Rust。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "language":    {"type": "string", "enum": ["typescript", "python", "go", "java", "rust", "cpp"], "description": "目标语言"},
                "requirement": {"type": "string", "description": "用自然语言描述代码需求"},
                "framework":   {"type": "string", "description": "使用的框架或库（可选）"},
            },
            "required": ["language", "requirement"],
        },
    },
    {
        "name": "refactor_code",
        "description": "对现有代码进行重构，提出改进建议并生成重构后的代码。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code":     {"type": "string", "description": "需要重构的代码"},
                "language": {"type": "string", "description": "代码语言"},
                "goal": {
                    "type": "string",
                    "enum": ["readability", "performance", "testability", "simplicity"],
                    "description": "重构目标",
                },
            },
            "required": ["code", "language"],
        },
    },
]


# ─── Prompt 构建 ─────────────────────────────────────────────────────
def build_prompt(name: str, args: dict) -> str | None:
    if name == "code_review":
        code      = args.get("code")
        language  = args.get("language", "auto")
        repo_path = args.get("repo_path")
        repo_url  = args.get("repo_url")
        focus     = args.get("focus", "all")

        if repo_url:
            return (
                f"请 clone 仓库 {repo_url}，然后对代码进行完整审查。\n"
                f"重点方向：{focus}\n"
                f"要求：安全漏洞、代码质量、性能问题、规范遵从，并给出可执行改进建议。"
            )
        elif repo_path:
            return (
                f"请审查本地代码仓库：\n路径: {repo_path}\n"
                f"语言: {language}\n重点方向: {focus}\n\n"
                f"要求：安全漏洞、代码质量、性能问题、规范遵从，并给出可执行改进建议。"
            )
        elif code:
            return (
                f"请审查以下代码（语言：{language}），重点方向：{focus}\n"
                f"```\n{code}\n```\n\n"
                f"要求：安全漏洞、代码质量、性能问题、规范遵从，并给出可执行改进建议。"
            )

    elif name == "code_audit":
        repo_path = args.get("repo_path")
        repo_url  = args.get("repo_url")
        level     = args.get("level", "fast")
        target    = f"URL: {repo_url}" if repo_url else f"路径: {repo_path}"
        return (
            f"对代码仓库进行深度的{'全面' if level=='full' else '快速'}安全+质量审计。\n"
            f"{target}\n\n"
            f"执行：CVE 漏洞扫描、依赖许可证审计、安全配置检查、代码规范审计，输出结构化审计报告。"
        )

    elif name == "generate_code":
        language    = args.get("language", "")
        requirement = args.get("requirement", "")
        framework   = args.get("framework", "")
        return (
            f"生成高质量 {language} 代码。\n"
            f"需求：{requirement}\n"
            f"{'框架：' + framework if framework else ''}\n\n"
            f"要求：类型标注完整、错误处理规范、Clean Code 原则、基本单元测试。"
        )

    elif name == "refactor_code":
        code     = args.get("code", "")
        language = args.get("language", "auto")
        goal     = args.get("goal", "readability")
        return (
            f"重构以下 {language} 代码，目标：{goal}。\n"
            f"```\n{code}\n```\n\n"
            f"先分析问题，再提供重构后完整代码，解释改进点。"
        )

    return None


# ─── MCP 协议处理 ────────────────────────────────────────────────────
def send_response(req_id, result):
    print(json.dumps({"jsonrpc": "2.0", "id": req_id, "result": result}, ensure_ascii=False), flush=True)


def send_error(req_id, code, message):
    print(json.dumps({"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}, ensure_ascii=False), flush=True)


def send_notification(method, params):
    print(json.dumps({"jsonrpc": "2.0", "method": method, "params": params}, ensure_ascii=False), flush=True)


def main():
    send_notification("initialized", {
        "protocolVersion": PROTOCOL_VERSION,
        "capabilities":   {"tools": {}},
        "serverInfo":    {"name": SERVER_NAME, "version": SERVER_VERSION},
    })

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = msg.get("method")
        req_id = msg.get("id")
        params = msg.get("params", {})

        if method == "tools/list":
            send_response(req_id, {"tools": TOOLS})

        elif method == "tools/call":
            name      = params.get("name")
            arguments = params.get("arguments", {})
            if isinstance(arguments, list):
                arguments = {}

            # 参数校验
            if name == "code_review":
                if not any([arguments.get("code"), arguments.get("repo_path"), arguments.get("repo_url")]):
                    send_error(req_id, -32602, "code 或 repo_path 或 repo_url 至少提供一个")
                    continue
            elif name == "code_audit":
                if not any([arguments.get("repo_path"), arguments.get("repo_url")]):
                    send_error(req_id, -32602, "repo_path 或 repo_url 至少提供一个")
                    continue
            elif name == "generate_code":
                if not arguments.get("requirement"):
                    send_error(req_id, -32602, "requirement 参数必填")
                    continue
            elif name == "refactor_code":
                if not arguments.get("code"):
                    send_error(req_id, -32602, "code 参数必填")
                    continue
            else:
                send_error(req_id, -32601, f"未知工具: {name}")
                continue

            prompt = build_prompt(name, arguments)
            if prompt is None:
                send_error(req_id, -32602, "参数错误")
                continue

            result_text = call_minimax(CODE_EXPERT_SYSTEM, prompt)
            send_response(req_id, {"content": [{"type": "text", "text": result_text}]})

        elif method == "ping":
            send_response(req_id, {})


if __name__ == "__main__":
    main()
