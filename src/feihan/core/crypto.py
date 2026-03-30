# Copyright (c) 2026 上海飞函安全科技有限公司 (Shanghai Feihan Security Technology Co., Ltd.)
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import gzip
import hashlib
import os
import string
from dataclasses import dataclass
from typing import TYPE_CHECKING

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding

if TYPE_CHECKING:
    from feihan.core.config import Config

from feihan.core.consts import DEFAULT_SECURE_VERSION

_ALPHANUMERIC = string.ascii_letters + string.digits


@dataclass
class SecureMessage:
    version: str = ""
    timestamp: int = 0
    nonce: str = ""
    encrypted_key: bytes = b""
    encrypted_data: bytes = b""


def sha256_hex(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()


def sha256_bytes(data: str) -> bytes:
    return hashlib.sha256(data.encode()).digest()


def _random_alphanumeric(size: int) -> str:
    return "".join(_ALPHANUMERIC[b % 62] for b in os.urandom(size))


def _encrypt_aes256_cbc(data: bytes, key: bytes) -> bytes:
    iv = os.urandom(16)
    padder = padding.PKCS7(128).padder()
    padded = padder.update(data) + padder.finalize()
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    encrypted = encryptor.update(padded) + encryptor.finalize()
    return iv + encrypted


def _decrypt_aes256_cbc(data: bytes, key: bytes) -> bytes:
    if len(data) < 16 or len(data) % 16 != 0:
        raise ValueError("invalid encrypted data length")
    iv = data[:16]
    ciphertext = data[16:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    padded = decryptor.update(ciphertext) + decryptor.finalize()
    unpadder = padding.PKCS7(128).unpadder()
    return unpadder.update(padded) + unpadder.finalize()


class CryptoManager:
    def __init__(self, config: Config) -> None:
        self._config = config
        self._prefix = _random_alphanumeric(6)
        self._counter = [0, 0, 0, 0, 0]

    def encrypt_message(self, secret: str, data: bytes) -> SecureMessage:
        timestamp = self._config.time_manager.get_server_timestamp()
        nonce = self._get_nonce()

        init_key = sha256_bytes(f"{timestamp}:{secret}:{nonce}")
        aes_key = os.urandom(32)
        compressed = gzip.compress(data)
        encrypted_key = _encrypt_aes256_cbc(aes_key, init_key)
        encrypted_data = _encrypt_aes256_cbc(compressed, aes_key)

        return SecureMessage(
            version=DEFAULT_SECURE_VERSION,
            timestamp=timestamp,
            nonce=nonce,
            encrypted_key=encrypted_key,
            encrypted_data=encrypted_data,
        )

    def decrypt_message(self, secret: str, message: SecureMessage) -> bytes:
        if message.version != DEFAULT_SECURE_VERSION:
            raise ValueError(f"unsupported secure message version: {message.version}")

        init_key = sha256_bytes(f"{message.timestamp}:{secret}:{message.nonce}")
        aes_key = _decrypt_aes256_cbc(message.encrypted_key, init_key)
        compressed = _decrypt_aes256_cbc(message.encrypted_data, aes_key)
        return gzip.decompress(compressed)

    def _get_nonce(self) -> str:
        random_part = _random_alphanumeric(5)
        counter = self._format_counter()
        self._add_counter()
        return self._prefix + random_part + counter

    def _format_counter(self) -> str:
        return "".join(_ALPHANUMERIC[c] for c in self._counter)

    def _add_counter(self) -> None:
        for i in range(4, -1, -1):
            self._counter[i] += 1
            if self._counter[i] < 62:
                break
            self._counter[i] = 0
