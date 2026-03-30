# Copyright (c) 2026 上海飞函安全科技有限公司 (Shanghai Feihan Security Technology Co., Ltd.)
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import asyncio
import json
import random
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable, TYPE_CHECKING

import websockets
import websockets.asyncio.client

from feihan.core.consts import DEFAULT_WS_PATH
from feihan.core.types import EventHeader, WrappedEventHandler
from feihan.core.version import USER_AGENT
from feihan.internal.transport import (
    HttpRequest,
    HttpResponse,
    decode_http_response,
    decode_secure_message,
    decode_websocket_message,
    encode_http_request,
    encode_secure_message,
    encode_websocket_message,
)

if TYPE_CHECKING:
    from feihan.core.config import Config
    from feihan.core.crypto import CryptoManager

RECONNECT_CHECK_INTERVAL = 10.0
HEALTH_CHECK_INTERVAL = 20.0
ALIVE_TIMEOUT = 40.0
CONNECT_TIMEOUT = 5.0
WRITE_TIMEOUT = 60.0


class WsClient:
    def __init__(
        self,
        config: Config,
        get_secret: Callable[[], str],
        get_token: Callable[[], Awaitable[str]],
        ensure_ping: Callable[[], Awaitable[None]],
        crypto_manager: CryptoManager,
    ) -> None:
        self._config = config
        self._get_secret = get_secret
        self._get_token = get_token
        self._ensure_ping = ensure_ping
        self._crypto_manager = crypto_manager

        self._event_handlers: dict[str, list[WrappedEventHandler]] = {}
        self._socket: Any = None
        self._is_connecting = False
        self._should_close = False
        self._req_count = 0
        self._req_callbacks: dict[str, asyncio.Future[HttpResponse]] = {}
        self._reconnect_attempt = 0
        self._last_message_at = 0.0
        self._tasks: list[asyncio.Task[Any]] = []
        self._init_done = False
        self._init_task: asyncio.Task[None] | None = None

    def on_event(self, event_type: str, handler: WrappedEventHandler) -> None:
        self._ensure_init()
        handlers = self._event_handlers.setdefault(event_type, [])
        handlers.append(handler)

    def off_event(self, event_type: str, handler: WrappedEventHandler) -> None:
        handlers = self._event_handlers.get(event_type)
        if handlers and handler in handlers:
            handlers.remove(handler)

    async def http_request(self, req: HttpRequest) -> HttpResponse:
        await self._ensure_init_async()

        self._req_count += 1
        req_id = str(self._req_count)
        req.req_id = req_id

        loop = asyncio.get_event_loop()
        future: asyncio.Future[HttpResponse] = loop.create_future()
        self._req_callbacks[req_id] = future

        try:
            await self._send_message({
                "http_request": {
                    "method": req.method,
                    "path": req.path,
                    "headers": req.headers,
                    "body": req.body,
                    "req_id": req_id,
                },
            })
            return await asyncio.wait_for(future, timeout=WRITE_TIMEOUT)
        except asyncio.TimeoutError:
            self._req_callbacks.pop(req_id, None)
            raise TimeoutError(f"websocket request timeout: {WRITE_TIMEOUT}s")
        except Exception:
            self._req_callbacks.pop(req_id, None)
            raise

    def close(self) -> None:
        self._should_close = True
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()
        if self._socket:
            try:
                asyncio.get_event_loop().create_task(self._socket.close())
            except Exception:
                pass
            self._socket = None
        for future in self._req_callbacks.values():
            if not future.done():
                future.set_exception(RuntimeError("websocket closed"))
        self._req_callbacks.clear()

    def _ensure_init(self) -> None:
        if self._init_done:
            return
        if not self._init_task:
            self._init_task = asyncio.ensure_future(self._do_init())

    async def _ensure_init_async(self) -> None:
        if self._init_done:
            return
        if not self._init_task:
            self._init_task = asyncio.ensure_future(self._do_init())
        await self._init_task

    async def _do_init(self) -> None:
        if self._init_done:
            return
        try:
            await self._ensure_ping()
            await self._connect()
            self._init_done = True
        except Exception as e:
            self._config.logger.error("ws init failed: %s", e)
            self._schedule_reconnect()

    async def _connect(self) -> None:
        if self._is_connecting:
            return
        self._is_connecting = True

        try:
            if self._socket:
                try:
                    await self._socket.close()
                except Exception:
                    pass
                self._socket = None

            for future in self._req_callbacks.values():
                if not future.done():
                    future.set_exception(RuntimeError("websocket reconnecting"))
            self._req_callbacks.clear()

            await self._ensure_ping()
            token = await self._get_token()

            ws_url = self._config.backend_url.replace("http", "ws", 1) + DEFAULT_WS_PATH + f"?token={token}"

            ws = await asyncio.wait_for(
                websockets.asyncio.client.connect(ws_url),
                timeout=CONNECT_TIMEOUT,
            )
            self._socket = ws

            # Send InitRequest
            await self._send_message({"init_request": {"user_agent": USER_AGENT}})

            # Wait for InitResponse
            raw = await asyncio.wait_for(ws.recv(), timeout=CONNECT_TIMEOUT)
            data = raw if isinstance(raw, bytes) else raw.encode()
            secure_msg = decode_secure_message(data)
            decrypted = self._crypto_manager.decrypt_message(self._get_secret(), secure_msg)
            ws_msg = decode_websocket_message(decrypted)
            if "init_response" not in ws_msg:
                raise RuntimeError("unexpected message during init")

            self._last_message_at = time.time()
            self._start_health_check()
            self._start_reconnect_check()
            self._start_message_loop()
            self._reconnect_attempt = 0

        finally:
            self._is_connecting = False

    def _start_message_loop(self) -> None:
        task = asyncio.ensure_future(self._message_loop())
        self._tasks.append(task)

    async def _message_loop(self) -> None:
        try:
            while self._socket and not self._should_close:
                try:
                    raw = await self._socket.recv()
                    data = raw if isinstance(raw, bytes) else raw.encode()
                    await self._handle_message(data)
                except Exception as e:
                    if not self._should_close:
                        self._config.logger.error("ws recv error: %s", e)
                        break
        finally:
            if not self._should_close:
                self._socket = None
                self._schedule_reconnect()

    async def _handle_message(self, data: bytes) -> None:
        self._last_message_at = time.time()

        secure_msg = decode_secure_message(data)
        decrypted = self._crypto_manager.decrypt_message(self._get_secret(), secure_msg)
        ws_msg = decode_websocket_message(decrypted)

        if "pong" in ws_msg:
            self._config.time_manager.sync_server_timestamp(ws_msg["pong"].get("timestamp", 0))
        elif "event" in ws_msg:
            event = ws_msg["event"]
            eh = event.get("event_header", {})
            header = EventHeader(
                event_id=eh.get("event_id", ""),
                event_type=eh.get("event_type", ""),
                event_created_at=str(eh.get("event_created_at", "0")),
            )
            handlers = self._event_handlers.get(header.event_type, [])
            for handler in handlers:
                try:
                    handler(header, event.get("event_body", b""))
                except Exception as e:
                    self._config.logger.error("event handler error: %s", e)
            # Send event ack
            try:
                await self._send_message({"event_ack": {"event_id": header.event_id}})
            except Exception:
                pass
        elif "http_response" in ws_msg:
            resp = ws_msg["http_response"]
            req_id = resp.get("req_id", "")
            future = self._req_callbacks.pop(req_id, None)
            if future and not future.done():
                future.set_result(HttpResponse(
                    status_code=resp.get("status_code", 0),
                    status_text=resp.get("status_text", ""),
                    headers=resp.get("headers", {}),
                    body=resp.get("body", b""),
                    req_id=req_id,
                ))

    async def _send_message(self, msg: dict[str, Any]) -> None:
        if not self._socket:
            raise RuntimeError("websocket not connected")
        msg_bytes = encode_websocket_message(msg)
        secure_msg = self._crypto_manager.encrypt_message(self._get_secret(), msg_bytes)
        data = encode_secure_message(secure_msg)
        await self._socket.send(data)

    def _schedule_reconnect(self) -> None:
        if self._should_close:
            return
        delay = self._get_reconnect_delay()
        self._config.logger.info("ws reconnecting in %.1fs (attempt %d)", delay, self._reconnect_attempt + 1)

        async def do_reconnect() -> None:
            await asyncio.sleep(delay)
            self._reconnect_attempt += 1
            try:
                await self._connect()
                self._config.logger.info("ws reconnected")
            except Exception as e:
                self._config.logger.error("ws reconnect failed: %s", e)
                self._schedule_reconnect()

        task = asyncio.ensure_future(do_reconnect())
        self._tasks.append(task)

    def _get_reconnect_delay(self) -> float:
        attempt = self._reconnect_attempt
        if attempt == 0:
            return 0.25 + random.random() * 0.25
        if attempt <= 4:
            return 0.75 + random.random() * 0.5
        base = min(10.0, max(0.75, (attempt - 4) * 2.0))
        jitter = random.random()
        return min(15.0, base + jitter)

    def _start_health_check(self) -> None:
        async def check() -> None:
            while not self._should_close:
                await asyncio.sleep(HEALTH_CHECK_INTERVAL)
                try:
                    timestamp = self._config.time_manager.get_server_timestamp()
                    await self._send_message({"ping": {"timestamp": timestamp}})
                except Exception:
                    pass

        task = asyncio.ensure_future(check())
        self._tasks.append(task)

    def _start_reconnect_check(self) -> None:
        async def check() -> None:
            while not self._should_close:
                await asyncio.sleep(RECONNECT_CHECK_INTERVAL)
                if time.time() - self._last_message_at > ALIVE_TIMEOUT:
                    self._config.logger.warn("ws alive timeout, reconnecting")
                    if self._socket:
                        try:
                            await self._socket.close()
                        except Exception:
                            pass
                        self._socket = None
                    self._schedule_reconnect()
                    return

        task = asyncio.ensure_future(check())
        self._tasks.append(task)
