# Copyright (c) 2026 上海飞函安全科技有限公司 (Shanghai Feihan Security Technology Co., Ltd.)
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import time


class DefaultTimeManager:
    def __init__(self) -> None:
        self._server_time_base: int = 0
        self._system_time_base: int = 0

    def get_system_timestamp(self) -> int:
        return int(time.time() * 1000)

    def get_server_timestamp(self) -> int:
        if self._server_time_base == 0:
            return self.get_system_timestamp()
        return self.get_system_timestamp() - self._system_time_base + self._server_time_base

    def sync_server_timestamp(self, timestamp: int) -> None:
        if timestamp <= self._server_time_base:
            return
        self._server_time_base = timestamp
        self._system_time_base = self.get_system_timestamp()
