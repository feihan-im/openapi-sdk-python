# Feihan IM OpenAPI SDK - Python

[![PyPI version](https://img.shields.io/pypi/v/feihan-sdk.svg)](https://pypi.org/project/feihan-sdk/)
[![CI](https://github.com/feihan-im/openapi-sdk-python/actions/workflows/ci.yaml/badge.svg)](https://github.com/feihan-im/openapi-sdk-python/actions/workflows/ci.yaml)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/github/license/feihan-im/openapi-sdk-python)](LICENSE)

English | [中文](README.md)

Feihan is a secure, self-hosted productivity platform, integrating instant messaging, organizational structures, video conferencing, and file storage.

This is the official Python SDK for Feihan server, used to interact with the Feihan server via OpenAPI. You need to deploy the Feihan server before using this SDK. See the [Quick Deploy Guide](https://feihanim.cn/docs/admin/install/quick-install) for setup instructions.

## Installation

```bash
pip install feihan-sdk
```

## Quick Start

```python
import asyncio
from feihan import FeihanClient, SendMessageReq, MessageContent, MessageText, MessageType_TEXT

async def main():
    client = await FeihanClient.create(
        "https://your-backend-url.com",
        "your-app-id",
        "your-app-secret",
    )

    # Optional: preheat fetches access token and syncs server time upfront,
    # reducing latency on the first API call
    await client.preheat()

    # Call API
    resp = await client.im.message.send_message(SendMessageReq(
        chat_id="chat-id",
        message_type=MessageType_TEXT,
        message_content=MessageContent(text=MessageText(content="Feihan new version released!")),
    ))
    print(resp.message_id)

    # Close when done
    await client.close()

asyncio.run(main())
```

## Configuration

`FeihanClient.create()` accepts optional keyword arguments to configure client behavior:

```python
from feihan import FeihanClient, LogLevel

client = await FeihanClient.create(
    "https://your-backend-url.com",
    "your-app-id",
    "your-app-secret",
    log_level=LogLevel.DEBUG,         # Log level (default: INFO)
    request_timeout=30.0,             # Request timeout in seconds (default: 60.0)
    enable_encryption=False,          # Enable request encryption (default: True)
)
```

## Event Subscription

Receive real-time events via WebSocket:

```python
from feihan import EventMessageReceive

def on_message(event: EventMessageReceive):
    print("Message received:", event.body)

client.im.message.event.on_message_receive(on_message)

# Unsubscribe
client.im.message.event.off_message_receive(on_message)
```

## Context Manager

Supports `async with` syntax for automatic cleanup:

```python
async with await FeihanClient.create(...) as client:
    resp = await client.im.message.send_message(SendMessageReq(...))
```

## Requirements

- **Python** 3.9+

## Links

- [Website](https://feihanim.cn/)

## License

[Apache-2.0 License](LICENSE)
