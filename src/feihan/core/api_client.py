# Copyright (c) 2026 上海飞函安全科技有限公司 (Shanghai Feihan Security Technology Co., Ltd.)
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import asyncio
import json
import os
import string
import time
from typing import Any, TYPE_CHECKING
from urllib.parse import urlencode

from feihan.core.consts import (
    DEFAULT_GATEWAY_PATH,
    DEFAULT_PING_PATH,
    DEFAULT_TOKEN_PATH,
)
from feihan.core.crypto import CryptoManager, sha256_hex
from feihan.core.types import (
    ApiError,
    ApiRequest,
    ApiResponse,
    EventHeader,
    WrappedEventHandler,
)
from feihan.core.version import USER_AGENT
from feihan.core.ws_client import WsClient
from feihan.internal.transport import (
    HttpRequest,
    decode_http_response,
    decode_secure_message,
    encode_http_request,
    encode_secure_message,
)

if TYPE_CHECKING:
    from feihan.core.config import Config

TIMESTAMP_HEADER = "X-Feihan-Timestamp"
NONCE_HEADER = "X-Feihan-Nonce"

_ALPHANUMERIC = string.ascii_letters + string.digits


def _random_alphanumeric(size: int) -> str:
    return "".join(_ALPHANUMERIC[b % 62] for b in os.urandom(size))


def _random_int(max_val: int) -> int:
    return int.from_bytes(os.urandom(8), "big") % max_val


def _unwrap_api_response(raw: Any) -> Any:
    code = raw.get("code", -1)
    if code != 0:
        raise ApiError(code, raw.get("msg", "unknown error"), raw.get("log_id", ""), raw.get("data"))
    return raw.get("data")


class DefaultApiClient:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._secret = ""
        self._token = ""
        self._token_refresh_at: int = 0
        self._token_expires_at: int = 0
        self._token_fetching = False
        self._token_lock: asyncio.Lock = asyncio.Lock()
        self._ping_called = False
        self._ping_expires_at: int = 0
        self._crypto_manager = CryptoManager(config)
        self._ws = WsClient(
            config=config,
            get_secret=lambda: self._secret,
            get_token=self._get_token,
            ensure_ping=self._ensure_ping,
            crypto_manager=self._crypto_manager,
        )

    async def init(self) -> None:
        self._secret = sha256_hex(f"{self._config.app_id}:{self._config.app_secret}")

    async def preheat(self) -> None:
        await self._ensure_ping()
        await self._get_token()

    async def close(self) -> None:
        self._ws.close()

    def on_event(self, event_type: str, handler: WrappedEventHandler) -> None:
        self._ws.on_event(event_type, handler)

    def off_event(self, event_type: str, handler: WrappedEventHandler) -> None:
        self._ws.off_event(event_type, handler)

    async def request(self, req: ApiRequest) -> ApiResponse:
        await self._ensure_ping()

        path = req.path
        if req.path_params:
            for key, value in req.path_params.items():
                path = path.replace(f":{key}", value)

        url = self._config.backend_url + path
        if req.query_params:
            url += "?" + urlencode(req.query_params)

        # Encrypted path
        if self._config.enable_encryption and req.with_app_access_token:
            token = await self._get_token()
            body_bytes = json.dumps(req.body).encode() if req.body else b""

            headers: dict[str, str] = {
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
                TIMESTAMP_HEADER: str(self._config.time_manager.get_server_timestamp()),
                NONCE_HEADER: _random_alphanumeric(16),
            }
            if req.header_params:
                headers.update(req.header_params)

            http_req = HttpRequest(
                method=req.method,
                path=url.replace(self._config.backend_url, ""),
                headers=headers,
                body=body_bytes,
                req_id="",
            )

            # WebSocket path
            if req.with_web_socket:
                if "Authorization" not in headers:
                    headers["Authorization"] = f"Bearer {token}"
                http_resp = await self._ws.http_request(http_req)
                data = _unwrap_api_response(json.loads(http_resp.body))
                return ApiResponse(data)

            # Gateway path
            http_req_bytes = encode_http_request(http_req)
            secure_message = self._crypto_manager.encrypt_message(self._secret, http_req_bytes)
            secure_bytes = encode_secure_message(secure_message)

            gateway_url = self._config.backend_url + DEFAULT_GATEWAY_PATH
            resp = await self._config.http_client.request(
                "POST",
                gateway_url,
                headers={
                    "Content-Type": "application/x-protobuf",
                    "Authorization": f"Bearer {token}",
                    "User-Agent": USER_AGENT,
                },
                content=secure_bytes,
            )

            resp_secure_message = decode_secure_message(resp.content)
            decrypted_bytes = self._crypto_manager.decrypt_message(self._secret, resp_secure_message)
            http_resp = decode_http_response(decrypted_bytes)
            data = _unwrap_api_response(json.loads(http_resp.body))
            return ApiResponse(data)

        # Plain HTTP path
        timestamp = str(self._config.time_manager.get_server_timestamp())
        nonce = _random_alphanumeric(16)
        headers = {
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
            TIMESTAMP_HEADER: timestamp,
            NONCE_HEADER: nonce,
        }

        if req.with_app_access_token:
            token = await self._get_token()
            headers["Authorization"] = f"Bearer {token}"
        if req.header_params:
            for key, value in req.header_params.items():
                if value:
                    headers[key] = value

        resp = await self._config.http_client.request(
            req.method,
            url,
            headers=headers,
            json_data=req.body if req.body and req.method != "GET" else None,
        )

        data = _unwrap_api_response(json.loads(resp.content))
        return ApiResponse(data)

    # --- Token management ---

    async def _get_token(self) -> str:
        now = self._config.time_manager.get_server_timestamp()

        # Token still fully valid
        if self._token and self._token_refresh_at > now:
            return self._token

        # Token expired or missing — block and fetch
        if not self._token or self._token_expires_at <= now:
            async with self._token_lock:
                # Re-check after acquiring lock
                if not self._token or self._token_expires_at <= self._config.time_manager.get_server_timestamp():
                    await self._fetch_token()
            return self._token

        # Token near expiry — return current, refresh in background
        if not self._token_fetching:
            self._token_fetching = True

            async def _bg_refresh() -> None:
                try:
                    await self._fetch_token()
                finally:
                    self._token_fetching = False

            asyncio.ensure_future(_bg_refresh())

        return self._token

    async def _fetch_token(self) -> None:
        timestamp = self._config.time_manager.get_server_timestamp()
        nonce = _random_int(10**12)
        sign_payload = f"{self._config.app_id}:{timestamp}:{self._config.app_secret}:{nonce}"
        signature = sha256_hex(sign_payload)

        url = self._config.backend_url + DEFAULT_TOKEN_PATH
        resp = await self._config.http_client.request(
            "POST",
            url,
            headers={
                "Content-Type": "application/json",
                "User-Agent": USER_AGENT,
            },
            json_data={
                "app_id": self._config.app_id,
                "signature_version": "v1",
                "signature": signature,
                "timestamp": timestamp,
                "nonce": nonce,
            },
        )

        data = json.loads(resp.content)
        if data.get("code") != 0 or not data.get("data"):
            raise RuntimeError(f"fetch token failed: code={data.get('code')}, msg={data.get('msg')}")

        token_data = data["data"]
        self._token = token_data["app_access_token"]
        now = self._config.time_manager.get_server_timestamp()
        self._token_expires_at = now + (token_data["app_access_token_expires_in"] - 60) * 1000
        self._token_refresh_at = self._token_expires_at - 5 * 60 * 1000

    # --- Ping / server time sync ---

    async def _ensure_ping(self) -> None:
        now = int(time.time() * 1000)

        if self._ping_called and self._ping_expires_at > now:
            return

        await self._fetch_ping()

    async def _fetch_ping(self) -> None:
        url = self._config.backend_url + DEFAULT_PING_PATH
        resp = await self._config.http_client.request(
            "GET",
            url,
            headers={"User-Agent": USER_AGENT},
        )

        data = json.loads(resp.content)
        if data.get("code") != 0 or not data.get("data"):
            raise RuntimeError(f"ping failed: code={data.get('code')}, msg={data.get('msg')}")

        ping_data = data["data"]
        self._config.time_manager.sync_server_timestamp(ping_data["timestamp"])
        self._ping_called = True
        self._ping_expires_at = int(time.time() * 1000) + 60 * 60 * 1000
        self._config.logger.info(
            "ping ok, server version=%s, org_code=%s",
            ping_data.get("version", ""),
            ping_data.get("org_code", ""),
        )
