# Copyright (c) 2026 上海飞函安全科技有限公司 (Shanghai Feihan Security Technology Co., Ltd.)
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from feihan.core.config import Config
from feihan.core.api_client import DefaultApiClient
from feihan.core.http_client import DefaultHttpClient
from feihan.core.logger import DefaultLogger
from feihan.core.time_manager import DefaultTimeManager
from feihan.core.types import LogLevel
from feihan.core.crypto import sha256_hex
from feihan.service.im import Service as ImService


class FeihanClient:
    """OpenAPI SDK client."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.api_client = config.api_client
        self.im = ImService(config)

    @classmethod
    async def create(
        cls,
        backend_url: str,
        app_id: str,
        app_secret: str,
        *,
        request_timeout: float = 60.0,
        enable_encryption: bool = True,
        log_level: LogLevel = LogLevel.INFO,
    ) -> FeihanClient:
        """Create a new client instance."""
        backend_url = backend_url.rstrip("/")

        logger = DefaultLogger(log_level)
        http_client = DefaultHttpClient(request_timeout)
        time_manager = DefaultTimeManager()

        config = Config(
            app_id=app_id,
            app_secret=app_secret,
            backend_url=backend_url,
            http_client=http_client,
            api_client=None,  # type: ignore[arg-type]
            enable_encryption=enable_encryption,
            request_timeout=request_timeout,
            time_manager=time_manager,
            logger=logger,
        )

        api_client = DefaultApiClient(config)
        await api_client.init()
        config.api_client = api_client

        return cls(config)

    async def preheat(self) -> None:
        """Preheat the client by fetching token and syncing server time."""
        await self.api_client.preheat()

    async def close(self) -> None:
        """Close the client and release resources."""
        await self.api_client.close()

    async def __aenter__(self) -> FeihanClient:
        return self

    async def __aexit__(self, *args: object) -> None:
        await self.close()
