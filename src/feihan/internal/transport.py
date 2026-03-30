# Copyright (c) 2026 上海飞函安全科技有限公司 (Shanghai Feihan Security Technology Co., Ltd.)
# SPDX-License-Identifier: Apache-2.0

"""Self-contained protobuf encode/decode for transport.proto.
Implements minimal protobuf wire format (varint + length-delimited) with zero dependencies.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from typing import Any


# ---- Minimal Protobuf Writer ----

class ProtoWriter:
    def __init__(self) -> None:
        self._buf = bytearray(256)
        self._pos = 0
        self._fork_stack: list[int] = []

    def _grow(self, need: int) -> None:
        while self._pos + need > len(self._buf):
            self._buf.extend(b"\x00" * len(self._buf))

    def uint32(self, value: int) -> ProtoWriter:
        self._grow(5)
        value &= 0xFFFFFFFF
        while value > 127:
            self._buf[self._pos] = (value & 0x7F) | 0x80
            self._pos += 1
            value >>= 7
        self._buf[self._pos] = value
        self._pos += 1
        return self

    def uint64(self, value: int) -> ProtoWriter:
        self._grow(10)
        value &= 0xFFFFFFFFFFFFFFFF
        while value > 127:
            self._buf[self._pos] = (value & 0x7F) | 0x80
            self._pos += 1
            value >>= 7
        self._buf[self._pos] = value
        self._pos += 1
        return self

    def int32(self, value: int) -> ProtoWriter:
        if value >= 0:
            return self.uint32(value)
        return self.uint64(value + (1 << 64))

    def write_bytes(self, value: bytes) -> ProtoWriter:
        self.uint32(len(value))
        self._grow(len(value))
        self._buf[self._pos:self._pos + len(value)] = value
        self._pos += len(value)
        return self

    def string(self, value: str) -> ProtoWriter:
        return self.write_bytes(value.encode("utf-8"))

    def fork(self) -> ProtoWriter:
        self._fork_stack.append(self._pos)
        self._grow(5)
        self._pos += 5
        return self

    def ldelim(self) -> ProtoWriter:
        start_pos = self._fork_stack.pop()
        content_start = start_pos + 5
        content_len = self._pos - content_start
        len_bytes = bytearray()
        v = content_len
        while v > 127:
            len_bytes.append((v & 0x7F) | 0x80)
            v >>= 7
        len_bytes.append(v)
        new_content_start = start_pos + len(len_bytes)
        self._buf[new_content_start:new_content_start + content_len] = self._buf[content_start:self._pos]
        self._buf[start_pos:start_pos + len(len_bytes)] = len_bytes
        self._pos = new_content_start + content_len
        return self

    def finish(self) -> bytes:
        return bytes(self._buf[:self._pos])


# ---- Minimal Protobuf Reader ----

class ProtoReader:
    def __init__(self, data: bytes) -> None:
        self._buf = data
        self.pos = 0
        self.length = len(data)

    def uint32(self) -> int:
        value = 0
        shift = 0
        while True:
            b = self._buf[self.pos]
            self.pos += 1
            value |= (b & 0x7F) << shift
            shift += 7
            if not (b & 0x80):
                break
        return value & 0xFFFFFFFF

    def uint64(self) -> int:
        value = 0
        shift = 0
        while True:
            b = self._buf[self.pos]
            self.pos += 1
            value |= (b & 0x7F) << shift
            shift += 7
            if not (b & 0x80):
                break
        return value

    def int32(self) -> int:
        v = self.uint32()
        if v > 0x7FFFFFFF:
            return v - 0x100000000
        return v

    def read_bytes(self) -> bytes:
        length = self.uint32()
        value = self._buf[self.pos:self.pos + length]
        self.pos += length
        return bytes(value)

    def string(self) -> str:
        return self.read_bytes().decode("utf-8")

    def skip_type(self, wire_type: int) -> None:
        if wire_type == 0:  # varint
            while self._buf[self.pos] & 0x80:
                self.pos += 1
            self.pos += 1
        elif wire_type == 1:  # 64-bit
            self.pos += 8
        elif wire_type == 2:  # length-delimited
            self.pos += self.uint32()
        elif wire_type == 5:  # 32-bit
            self.pos += 4
        else:
            raise ValueError(f"unknown wire type: {wire_type}")


# ---- SecureMessage ----

@dataclass
class _SecureMessage:
    version: str = ""
    timestamp: int = 0
    nonce: str = ""
    encrypted_key: bytes = b""
    encrypted_data: bytes = b""


def encode_secure_message(msg: Any) -> bytes:
    w = ProtoWriter()
    if msg.version:
        w.uint32(10).string(msg.version)
    if msg.timestamp:
        w.uint32(16).uint64(msg.timestamp)
    if msg.nonce:
        w.uint32(26).string(msg.nonce)
    if msg.encrypted_key:
        w.uint32(34).write_bytes(msg.encrypted_key)
    if msg.encrypted_data:
        w.uint32(42).write_bytes(msg.encrypted_data)
    return w.finish()


def decode_secure_message(data: bytes) -> Any:
    from feihan.core.crypto import SecureMessage
    r = ProtoReader(data)
    msg = SecureMessage()
    while r.pos < r.length:
        tag = r.uint32()
        field_num = tag >> 3
        if field_num == 1:
            msg.version = r.string()
        elif field_num == 2:
            msg.timestamp = r.uint64()
        elif field_num == 3:
            msg.nonce = r.string()
        elif field_num == 4:
            msg.encrypted_key = r.read_bytes()
        elif field_num == 5:
            msg.encrypted_data = r.read_bytes()
        else:
            r.skip_type(tag & 7)
    return msg


# ---- HttpRequest ----

@dataclass
class HttpRequest:
    method: str = ""
    path: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    req_id: str = ""


def encode_http_request(msg: HttpRequest) -> bytes:
    w = ProtoWriter()
    if msg.method:
        w.uint32(10).string(msg.method)
    if msg.path:
        w.uint32(18).string(msg.path)
    if msg.headers:
        for k, v in msg.headers.items():
            w.uint32(26).fork().uint32(10).string(k).uint32(18).string(v).ldelim()
    if msg.body:
        w.uint32(34).write_bytes(msg.body)
    if msg.req_id:
        w.uint32(42).string(msg.req_id)
    return w.finish()


def decode_http_request(data: bytes) -> HttpRequest:
    r = ProtoReader(data)
    msg = HttpRequest()
    while r.pos < r.length:
        tag = r.uint32()
        field_num = tag >> 3
        if field_num == 1:
            msg.method = r.string()
        elif field_num == 2:
            msg.path = r.string()
        elif field_num == 3:
            entry_end = r.uint32() + r.pos
            key = ""
            value = ""
            while r.pos < entry_end:
                entry_tag = r.uint32()
                ef = entry_tag >> 3
                if ef == 1:
                    key = r.string()
                elif ef == 2:
                    value = r.string()
                else:
                    r.skip_type(entry_tag & 7)
            msg.headers[key] = value
        elif field_num == 4:
            msg.body = r.read_bytes()
        elif field_num == 5:
            msg.req_id = r.string()
        else:
            r.skip_type(tag & 7)
    return msg


# ---- HttpResponse ----

@dataclass
class HttpResponse:
    status_code: int = 0
    status_text: str = ""
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""
    req_id: str = ""


def decode_http_response(data: bytes) -> HttpResponse:
    r = ProtoReader(data)
    msg = HttpResponse()
    while r.pos < r.length:
        tag = r.uint32()
        field_num = tag >> 3
        if field_num == 1:
            msg.status_code = r.int32()
        elif field_num == 2:
            msg.status_text = r.string()
        elif field_num == 3:
            entry_end = r.uint32() + r.pos
            key = ""
            value = ""
            while r.pos < entry_end:
                entry_tag = r.uint32()
                ef = entry_tag >> 3
                if ef == 1:
                    key = r.string()
                elif ef == 2:
                    value = r.string()
                else:
                    r.skip_type(entry_tag & 7)
            msg.headers[key] = value
        elif field_num == 4:
            msg.body = r.read_bytes()
        elif field_num == 5:
            msg.req_id = r.string()
        else:
            r.skip_type(tag & 7)
    return msg


# ---- WebSocketMessage ----

def encode_websocket_message(msg: dict[str, Any]) -> bytes:
    w = ProtoWriter()
    if "ping" in msg:
        w.uint32(10).fork()
        if msg["ping"].get("timestamp"):
            w.uint32(8).uint64(msg["ping"]["timestamp"])
        w.ldelim()
    if "pong" in msg:
        w.uint32(18).fork()
        if msg["pong"].get("timestamp"):
            w.uint32(8).uint64(msg["pong"]["timestamp"])
        w.ldelim()
    if "init_request" in msg:
        w.uint32(26).fork()
        if msg["init_request"].get("user_agent"):
            w.uint32(10).string(msg["init_request"]["user_agent"])
        w.ldelim()
    if "init_response" in msg:
        w.uint32(34).fork().ldelim()
    if "event" in msg:
        w.uint32(42).fork()
        eh = msg["event"].get("event_header")
        if eh:
            w.uint32(10).fork()
            if eh.get("event_id"):
                w.uint32(10).string(eh["event_id"])
            if eh.get("event_type"):
                w.uint32(18).string(eh["event_type"])
            if eh.get("event_created_at"):
                w.uint32(24).uint64(eh["event_created_at"])
            w.ldelim()
        eb = msg["event"].get("event_body")
        if eb:
            w.uint32(18).write_bytes(eb)
        w.ldelim()
    if "event_ack" in msg:
        w.uint32(50).fork()
        if msg["event_ack"].get("event_id"):
            w.uint32(10).string(msg["event_ack"]["event_id"])
        w.ldelim()
    if "http_request" in msg:
        req = msg["http_request"]
        http_req = HttpRequest(
            method=req.get("method", ""),
            path=req.get("path", ""),
            headers=req.get("headers", {}),
            body=req.get("body", b""),
            req_id=req.get("req_id", ""),
        )
        w.uint32(58).write_bytes(encode_http_request(http_req))
    return w.finish()


def decode_websocket_message(data: bytes) -> dict[str, Any]:
    r = ProtoReader(data)
    msg: dict[str, Any] = {}
    while r.pos < r.length:
        tag = r.uint32()
        field_num = tag >> 3
        if field_num == 1:  # ping
            sub_end = r.uint32() + r.pos
            ping: dict[str, Any] = {"timestamp": 0}
            while r.pos < sub_end:
                sub_tag = r.uint32()
                if (sub_tag >> 3) == 1:
                    ping["timestamp"] = r.uint64()
                else:
                    r.skip_type(sub_tag & 7)
            msg["ping"] = ping
        elif field_num == 2:  # pong
            sub_end = r.uint32() + r.pos
            pong: dict[str, Any] = {"timestamp": 0}
            while r.pos < sub_end:
                sub_tag = r.uint32()
                if (sub_tag >> 3) == 1:
                    pong["timestamp"] = r.uint64()
                else:
                    r.skip_type(sub_tag & 7)
            msg["pong"] = pong
        elif field_num == 3:  # initRequest
            sub_end = r.uint32() + r.pos
            init_req: dict[str, Any] = {"user_agent": ""}
            while r.pos < sub_end:
                sub_tag = r.uint32()
                if (sub_tag >> 3) == 1:
                    init_req["user_agent"] = r.string()
                else:
                    r.skip_type(sub_tag & 7)
            msg["init_request"] = init_req
        elif field_num == 4:  # initResponse
            sub_end = r.uint32() + r.pos
            r.pos = sub_end
            msg["init_response"] = {}
        elif field_num == 5:  # event
            sub_end = r.uint32() + r.pos
            event: dict[str, Any] = {"event_body": b""}
            while r.pos < sub_end:
                sub_tag = r.uint32()
                sf = sub_tag >> 3
                if sf == 1:
                    header_end = r.uint32() + r.pos
                    header: dict[str, Any] = {"event_id": "", "event_type": "", "event_created_at": 0}
                    while r.pos < header_end:
                        h_tag = r.uint32()
                        hf = h_tag >> 3
                        if hf == 1:
                            header["event_id"] = r.string()
                        elif hf == 2:
                            header["event_type"] = r.string()
                        elif hf == 3:
                            header["event_created_at"] = r.uint64()
                        else:
                            r.skip_type(h_tag & 7)
                    event["event_header"] = header
                elif sf == 2:
                    event["event_body"] = r.read_bytes()
                else:
                    r.skip_type(sub_tag & 7)
            msg["event"] = event
        elif field_num == 6:  # eventAck
            sub_end = r.uint32() + r.pos
            ack: dict[str, Any] = {"event_id": ""}
            while r.pos < sub_end:
                sub_tag = r.uint32()
                if (sub_tag >> 3) == 1:
                    ack["event_id"] = r.string()
                else:
                    r.skip_type(sub_tag & 7)
            msg["event_ack"] = ack
        elif field_num == 7:  # httpRequest
            raw = r.read_bytes()
            msg["http_request"] = decode_http_request(raw)
        elif field_num == 8:  # httpResponse
            raw = r.read_bytes()
            resp = decode_http_response(raw)
            msg["http_response"] = {
                "status_code": resp.status_code,
                "status_text": resp.status_text,
                "headers": resp.headers,
                "body": resp.body,
                "req_id": resp.req_id,
            }
        else:
            r.skip_type(tag & 7)
    return msg
