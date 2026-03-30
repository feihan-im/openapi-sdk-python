# Copyright (c) 2026 上海飞函安全科技有限公司 (Shanghai Feihan Security Technology Co., Ltd.)
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

from feihan.core.types import ApiRequest
from feihan.service.im.v1.message_model import (
    SendMessageReq,
    SendMessageResp,
    GetMessageReq,
    GetMessageResp,
    RecallMessageReq,
    RecallMessageResp,
    ReadMessageReq,
    ReadMessageResp,
)
from feihan.service.im.v1.message_event import MessageEvent

if TYPE_CHECKING:
    from feihan.core.config import Config


class Message:
    def __init__(self, config: Config) -> None:
        self._config = config
        self.event = MessageEvent(config)


    async def send_message(self, req: SendMessageReq) -> SendMessageResp:
        """发送消息"""
        body = req.to_dict()
        resp = await self._config.api_client.request(ApiRequest(
            method="POST",
            path="/oapi/im/v1/messages",
            body=body,
            with_app_access_token=True,
            with_web_socket=True,
        ))
        return SendMessageResp.from_dict(resp.json())

    async def get_message(self, req: GetMessageReq) -> GetMessageResp:
        """获取消息"""
        body = req.to_dict()
        resp = await self._config.api_client.request(ApiRequest(
            method="GET",
            path=f"/oapi/im/v1/messages/{body.get('message_id', '')}",
            body=body,
            with_app_access_token=True,
        ))
        return GetMessageResp.from_dict(resp.json())

    async def recall_message(self, req: RecallMessageReq) -> RecallMessageResp:
        """撤回消息"""
        body = req.to_dict()
        resp = await self._config.api_client.request(ApiRequest(
            method="POST",
            path=f"/oapi/im/v1/messages/{body.get('message_id', '')}/recall",
            body=body,
            with_app_access_token=True,
        ))
        return RecallMessageResp.from_dict(resp.json())

    async def read_message(self, req: ReadMessageReq) -> ReadMessageResp:
        """阅读消息"""
        body = req.to_dict()
        resp = await self._config.api_client.request(ApiRequest(
            method="POST",
            path=f"/oapi/im/v1/messages/{body.get('message_id', '')}/read",
            body=body,
            with_app_access_token=True,
        ))
        return ReadMessageResp.from_dict(resp.json())
