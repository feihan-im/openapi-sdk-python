# Copyright (c) 2026 上海飞函安全科技有限公司 (Shanghai Feihan Security Technology Co., Ltd.)
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass

from feihan.core.types import BaseModel


# 设置正在输入中（请求）
@dataclass
class CreateTypingReq(BaseModel):
    chat_id: str | None = None  # 聊天 id


# 设置正在输入中（响应）
@dataclass
class CreateTypingResp(BaseModel):
    pass


# 清除正在输入中（请求）
@dataclass
class DeleteTypingReq(BaseModel):
    chat_id: str | None = None  # 聊天 id


# 清除正在输入中（响应）
@dataclass
class DeleteTypingResp(BaseModel):
    pass

