# Copyright (c) 2026 上海飞函安全科技有限公司 (Shanghai Feihan Security Technology Co., Ltd.)
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import logging
from typing import Any

from feihan.core.types import LogLevel

_logger = logging.getLogger("Feihan")


class DefaultLogger:
    def __init__(self, level: LogLevel = LogLevel.INFO) -> None:
        self._level = level
        if not _logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("[Feihan] %(levelname)s %(message)s"))
            _logger.addHandler(handler)
        _logger.setLevel(self._to_logging_level(level))

    @staticmethod
    def _to_logging_level(level: LogLevel) -> int:
        mapping = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARN: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
        }
        return mapping.get(level, logging.INFO)

    def debug(self, msg: str, *args: Any) -> None:
        _logger.debug(msg, *args)

    def info(self, msg: str, *args: Any) -> None:
        _logger.info(msg, *args)

    def warn(self, msg: str, *args: Any) -> None:
        _logger.warning(msg, *args)

    def error(self, msg: str, *args: Any) -> None:
        _logger.error(msg, *args)
