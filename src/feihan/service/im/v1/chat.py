# Copyright (c) 2026 上海飞函安全科技有限公司 (Shanghai Feihan Security Technology Co., Ltd.)
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from typing import TYPE_CHECKING

from feihan.core.types import ApiRequest
from feihan.service.im.v1.chat_model import (
    CreateTypingReq,
    CreateTypingResp,
    DeleteTypingReq,
    DeleteTypingResp,
)

if TYPE_CHECKING:
    from feihan.core.config import Config


class Chat:
    def __init__(self, config: Config) -> None:
        self._config = config


    async def create_typing(self, req: CreateTypingReq) -> CreateTypingResp:
        """设置正在输入中
        
        设置正在输入中的状态，只持续五秒，仅限私聊
        """
        body = req.to_dict()
        resp = await self._config.api_client.request(ApiRequest(
            method="POST",
            path=f"/oapi/im/v1/chats/{body.get('chat_id', '')}/typing",
            body=body,
            with_app_access_token=True,
        ))
        return CreateTypingResp.from_dict(resp.json())

    async def delete_typing(self, req: DeleteTypingReq) -> DeleteTypingResp:
        """清除正在输入中
        
        仅限单聊
        """
        body = req.to_dict()
        resp = await self._config.api_client.request(ApiRequest(
            method="DELETE",
            path=f"/oapi/im/v1/chats/{body.get('chat_id', '')}/typing",
            body=body,
            with_app_access_token=True,
        ))
        return DeleteTypingResp.from_dict(resp.json())
