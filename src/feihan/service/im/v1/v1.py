# Copyright (c) 2026 上海飞函安全科技有限公司 (Shanghai Feihan Security Technology Co., Ltd.)
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from feihan.core.config import Config

from feihan.service.im.v1.chat import Chat
from feihan.service.im.v1.message import Message


class V1:
    def __init__(self, config: Config) -> None:
        self.chat = Chat(config)
        self.message = Message(config)
