# Google Stitch MCP Proxy

这是一个用于 Prefect Horizon 的单一 FastMCP 项目。它把 Google Stitch 的远程 MCP：

```text
https://stitch.googleapis.com/mcp
```

代理为 Horizon 生成的单一 Streamable HTTP MCP 地址：

```text
https://<server-name>.fastmcp.app/mcp
```

连接代理的客户端不需要再提供 `X-Goog-Api-Key`。代理会从服务器环境变量读取密钥，并在请求上游 Stitch MCP 时注入该请求头。

## 安全设计

真实密钥不会写入源码或 `.env.example`。部署环境必须提供：

```text
GOOGLE_API_KEY=<your-google-stitch-api-key>
```

请把它配置为 Horizon 部署环境中的 Secret/环境变量，不要提交到 GitHub。由于代理 URL 的使用者会间接消耗这把 Google API Key，部署时建议启用 Horizon Authentication，不要把未鉴权地址公开传播。

## Horizon 配置

如果仓库根目录就是本目录：

```text
Entrypoint: main.py:mcp
```

如果把本目录保留为主仓库中的子目录，则 Entrypoint 使用：

```text
stitch-mcp-proxy/main.py:mcp
```

依赖由 `requirements.txt` 自动检测。部署完成后的客户端连接地址为：

```text
https://<server-name>.fastmcp.app/mcp
```

## 本地运行（可选）

先在当前终端设置环境变量，然后运行：

```powershell
$env:GOOGLE_API_KEY = "your-key"
fastmcp run main.py:mcp --transport http --port 8000
```

本地端点通常是：

```text
http://localhost:8000/mcp
```

## 工作方式

```text
ChatGPT / MCP 客户端
        |
        | 不携带 Google API Key
        v
Horizon: /mcp
        |
        | X-Goog-Api-Key: 从 GOOGLE_API_KEY 注入
        v
https://stitch.googleapis.com/mcp
```

该代理会转发上游 MCP 的工具、资源、提示和工具调用，而不是重新手工实现 Stitch 工具。

## 排查上游 401

如果 Horizon 中调用 Stitch 工具时返回 `401 Unauthorized`，先确认错误来自
`https://stitch.googleapis.com/mcp`，而不是 Horizon 的访问认证。

### 防止错误转发下游 Bearer Token

FastMCP 的 `create_proxy(...)` 默认会将下游请求中的
`Authorization` 头转发给上游。对受 Horizon Authentication 保护的部署，
这个头是 Horizon/客户端的 Bearer token，并不属于 Google Stitch。

如果把它与 `X-Goog-Api-Key` 一起发送给 Stitch，Stitch 可能优先处理无效的
Bearer token 并返回 401。此项目在创建代理后明确关闭该行为：

```python
mcp = create_proxy(upstream_transport, name="Google Stitch MCP Proxy")
upstream_transport.forward_incoming_headers = False
```

不要移除这项设置。上游 Stitch 请求应只使用服务器端配置的
`X-Goog-Api-Key`；客户端不应提供 Google API key，也不应将 Horizon 的访问
token 用作 Stitch 凭据。

### 安全诊断日志

启动时，服务器会输出以下脱敏信息：

```text
Stitch proxy upstream authentication configured:
fastmcp_version=... key_length=... key_sha256_prefix=... header_present=True
```

它不记录完整密钥。若直连 Stitch 可用、代理仍返回 401，可将本地 key 计算出的
SHA-256 前 8 位与 `key_sha256_prefix` 比较，以确认 Horizon 使用的是同一把 key。
不要在日志、Issue、截图或聊天中公开完整 key。

依赖固定为 `fastmcp==3.4.4`，以避免重部署时因浮动的 FastMCP 版本改变代理行为。
