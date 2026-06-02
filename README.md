# code-expert MCP

通过 MiniMax API 驱动的代码审查 MCP Server，直接调 LLM，不依赖 OpenClaw。

通过 MCP stdio 暴露给 Claude Desktop / Cursor / Cline 等 MCP 客户端。

## 安装

```bash
uv tool install "git+https://github.com/Ariesssssssss/test1.git"
```

## 配置

安装后设置环境变量：

**macOS/Linux (bash/zsh):**
```bash
export MINIMAX_API_KEY="你的MiniMax API Secret Key"
export MINIMAX_MODEL="MiniMax-M3"   # 可选，默认 MiniMax-M3
```

**Windows (PowerShell):**
```powershell
$env:MINIMAX_API_KEY = "你的MiniMax API Secret Key"
$env:MINIMAX_MODEL = "MiniMax-M3"
```

**永久保存 (Windows):**
```powershell
[System.Environment]::SetEnvironmentVariable("MINIMAX_API_KEY", "你的Key", "User")
```

## Claude Desktop 配置

编辑 `%APPDATA%\Claude\claude_desktop_config.json`：

```json
{
  "mcpServers": {
    "code-expert": {
      "command": "code-expert"
    }
  }
}
```

**如果 uv tool install 方式不行，用 python 直接跑：**

```json
{
  "mcpServers": {
    "code-expert": {
      "command": "python",
      "args": ["C:/path/to/code_expert_mcp/server.py"],
      "env": {
        "MINIMAX_API_KEY": "你的MiniMax API Secret Key",
        "MINIMAX_MODEL": "MiniMax-M3"
      }
    }
  }
}
```

## MiniMax API Key 获取

1. 访问 https://platform.minimaxi.com
2. 注册/登录后创建 API Key
3. 格式：`sk-cp-xxxxxxxxxx`

## 工具

| 工具 | 说明 |
|------|------|
| `code_review` | 代码审查（安全/质量/性能/架构） |
| `code_audit` | 深度安全+质量审计 |
| `generate_code` | 自然语言生成代码 |
| `refactor_code` | 重构建议+代码 |

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MINIMAX_API_KEY` | **必填** | MiniMax API Secret Key |
| `MINIMAX_MODEL` | `MiniMax-M3` | 模型名 |
| `MINIMAX_TIMEOUT` | `120` | 单次调用超时（秒） |

## 依赖

- Python 3.8+
- 标准库（无需第三方包）
