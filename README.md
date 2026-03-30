# 飞函 IM OpenAPI SDK - Python

[![PyPI version](https://img.shields.io/pypi/v/feihan-sdk.svg)](https://pypi.org/project/feihan-sdk/)
[![CI](https://github.com/feihan-im/openapi-sdk-python/actions/workflows/ci.yaml/badge.svg)](https://github.com/feihan-im/openapi-sdk-python/actions/workflows/ci.yaml)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/github/license/feihan-im/openapi-sdk-python)](LICENSE)

[English](README_en.md) | 中文

飞函，是安全稳定的私有化一站式办公平台，功能包括即时通讯、组织架构、音视频会议、网盘等。

本项目是飞函服务端的 Python SDK，用于通过 OpenAPI 与飞函服务端进行交互。使用前需要先自行部署飞函服务端，部署教程请参考[快速部署文档](https://feihanim.cn/docs/admin/install/quick-install)。

## 安装

```bash
pip install feihan-sdk
```

## 快速开始

```python
import asyncio
from feihan import FeihanClient, SendMessageReq, MessageContent, MessageText, MessageType_TEXT

async def main():
    client = await FeihanClient.create(
        "https://your-backend-url.com",
        "your-app-id",
        "your-app-secret",
    )

    # 可选：预热可提前获取访问凭证和同步服务端时间，减少首次调用的延迟
    await client.preheat()

    # 调用 API
    resp = await client.im.message.send_message(SendMessageReq(
        chat_id="chat-id",
        message_type=MessageType_TEXT,
        message_content=MessageContent(text=MessageText(content="飞函新版本发布！")),
    ))
    print(resp.message_id)

    # 使用完毕后关闭
    await client.close()

asyncio.run(main())
```

## 客户端配置

`FeihanClient.create()` 支持通过关键字参数配置客户端行为：

```python
from feihan import FeihanClient, LogLevel

client = await FeihanClient.create(
    "https://your-backend-url.com",
    "your-app-id",
    "your-app-secret",
    log_level=LogLevel.DEBUG,         # 日志级别（默认: INFO）
    request_timeout=30.0,             # 请求超时秒数（默认: 60.0）
    enable_encryption=False,          # 启用请求加密（默认: True）
)
```

## 事件订阅

通过 WebSocket 接收实时事件推送：

```python
from feihan import EventMessageReceive

def on_message(event: EventMessageReceive):
    print("收到消息:", event.body)

client.im.message.event.on_message_receive(on_message)

# 取消订阅
client.im.message.event.off_message_receive(on_message)
```

## 上下文管理器

支持 `async with` 语法自动关闭客户端：

```python
async with await FeihanClient.create(...) as client:
    resp = await client.im.message.send_message(SendMessageReq(...))
```

## 环境要求

- **Python** 3.9+

## 相关链接

- [官网](https://feihanim.cn/)

## 许可证

[Apache-2.0 License](LICENSE)
