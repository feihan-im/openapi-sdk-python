# Copyright (c) 2026 上海飞函安全科技有限公司 (Shanghai Feihan Security Technology Co., Ltd.)
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import dataclasses
import enum
import sys
import types
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol, TypeVar, Union, get_type_hints, get_origin, get_args


def _serialize(val: Any) -> Any:
    if isinstance(val, BaseModel):
        return val.to_dict()
    if isinstance(val, list):
        return [_serialize(item) for item in val]
    if isinstance(val, dict):
        return {k: _serialize(v) for k, v in val.items()}
    return val


def _unwrap_optional(tp: Any) -> Any:
    origin = get_origin(tp)
    args = get_args(tp)
    if origin is Union or (sys.version_info >= (3, 10) and isinstance(tp, types.UnionType)):
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            return non_none[0]
    return tp


def _deserialize(val: Any, field_type: Any) -> Any:
    if val is None:
        return None
    field_type = _unwrap_optional(field_type)
    origin = get_origin(field_type)
    args = get_args(field_type)
    if isinstance(val, dict) and isinstance(field_type, type) and issubclass(field_type, BaseModel):
        return field_type.from_dict(val)
    if origin is list and args:
        return [_deserialize(item, args[0]) for item in val]
    if origin is dict and len(args) >= 2:
        return {k: _deserialize(v, args[1]) for k, v in val.items()}
    return val


_T = TypeVar("_T", bound="BaseModel")


@dataclass
class BaseModel:
    """Base class for all generated model types."""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict, omitting None values."""
        result: dict[str, Any] = {}
        for f in dataclasses.fields(self):
            val = getattr(self, f.name)
            if val is None:
                continue
            result[f.name] = _serialize(val)
        return result

    @classmethod
    def from_dict(cls: type[_T], data: Union[dict[str, Any], None] = None) -> _T:
        """Create an instance from a dict."""
        if not data:
            return cls()
        hints = get_type_hints(cls)
        kwargs: dict[str, Any] = {}
        for f in dataclasses.fields(cls):
            if f.name not in data:
                continue
            kwargs[f.name] = _deserialize(data[f.name], hints[f.name])
        return cls(**kwargs)


class LogLevel(enum.IntEnum):
    DEBUG = 0
    INFO = 1
    WARN = 2
    ERROR = 3


@dataclass
class ApiRequest:
    method: str
    path: str
    path_params: dict[str, str] | None = None
    query_params: dict[str, str] | None = None
    header_params: dict[str, str] | None = None
    body: Any = None
    with_app_access_token: bool = False
    with_web_socket: bool = False


class ApiResponse:
    def __init__(self, data: Any) -> None:
        self._data = data

    def json(self) -> Any:
        return self._data


class ApiError(Exception):
    def __init__(self, code: int, msg: str, log_id: str = "", data: Any = None) -> None:
        super().__init__(f"ApiError[code={code}, logId={log_id}, msg={msg}]")
        self.code = code
        self.msg = msg
        self.log_id = log_id
        self.data = data


@dataclass
class EventHeader:
    event_id: str = ""
    event_type: str = ""
    event_created_at: str = "0"


WrappedEventHandler = Callable[[EventHeader, Union[bytes, str]], None]


class ApiClient(Protocol):
    async def preheat(self) -> None: ...
    async def request(self, req: ApiRequest) -> ApiResponse: ...
    def on_event(self, event_type: str, handler: WrappedEventHandler) -> None: ...
    def off_event(self, event_type: str, handler: WrappedEventHandler) -> None: ...
    async def close(self) -> None: ...


class HttpClient(Protocol):
    async def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        content: bytes | None = None,
        json_data: Any = None,
    ) -> HttpResponse: ...


@dataclass
class HttpResponse:
    status_code: int
    content: bytes
    headers: dict[str, str] = field(default_factory=dict)

    def json(self) -> Any:
        import json as _json
        return _json.loads(self.content)


class Logger(Protocol):
    def debug(self, msg: str, *args: Any) -> None: ...
    def info(self, msg: str, *args: Any) -> None: ...
    def warn(self, msg: str, *args: Any) -> None: ...
    def error(self, msg: str, *args: Any) -> None: ...


class TimeManager(Protocol):
    def get_system_timestamp(self) -> int: ...
    def get_server_timestamp(self) -> int: ...
    def sync_server_timestamp(self, timestamp: int) -> None: ...
