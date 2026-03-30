# Copyright (c) 2026 上海飞函安全科技有限公司 (Shanghai Feihan Security Technology Co., Ltd.)
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from feihan.core.types import ApiClient, HttpClient, Logger, TimeManager


@dataclass
class Config:
    app_id: str
    app_secret: str
    backend_url: str
    http_client: HttpClient
    api_client: ApiClient
    enable_encryption: bool
    request_timeout: float
    time_manager: TimeManager
    logger: Logger
