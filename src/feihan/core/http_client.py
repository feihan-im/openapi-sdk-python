# Copyright (c) 2026 上海飞函安全科技有限公司 (Shanghai Feihan Security Technology Co., Ltd.)
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import Any

import httpx

from feihan.core.types import HttpResponse


class DefaultHttpClient:
    def __init__(self, timeout: float = 60.0) -> None:
        self._client = httpx.AsyncClient(timeout=timeout)

    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        content: bytes | None = None,
        json_data: Any = None,
    ) -> HttpResponse:
        resp = await self._client.request(
            method,
            url,
            headers=headers,
            content=content,
            json=json_data,
        )
        return HttpResponse(
            status_code=resp.status_code,
            content=resp.content,
            headers=dict(resp.headers),
        )

    async def close(self) -> None:
        await self._client.aclose()
