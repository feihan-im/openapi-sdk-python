# Copyright (c) 2026 上海飞函安全科技有限公司 (Shanghai Feihan Security Technology Co., Ltd.)
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, TYPE_CHECKING

from feihan.core.types import EventHeader, WrappedEventHandler
from feihan.service.im.v1.message_model import (
    EventMessageReceiveBody,
)

if TYPE_CHECKING:
    from feihan.core.config import Config


@dataclass
class EventMessageReceive:
    header: EventHeader = field(default_factory=EventHeader)
    body: EventMessageReceiveBody = field(default_factory=EventMessageReceiveBody)


class MessageEvent:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._handler_map: dict[Any, WrappedEventHandler] = {}

    def on_message_receive(self, handler: Callable[[EventMessageReceive], None]) -> None:
        """接收消息"""
        def wrapped_handler(header: EventHeader, body: bytes | str) -> None:
            parsed = json.loads(body) if isinstance(body, (bytes, bytearray)) else json.loads(body)
            handler(EventMessageReceive(header=header, body=EventMessageReceiveBody.from_dict(parsed)))
        self._handler_map[handler] = wrapped_handler
        self._config.api_client.on_event("im.v1.message.receive", wrapped_handler)

    def off_message_receive(self, handler: Callable[[EventMessageReceive], None]) -> None:
        wrapped = self._handler_map.pop(handler, None)
        if wrapped is not None:
            self._config.api_client.off_event("im.v1.message.receive", wrapped)
