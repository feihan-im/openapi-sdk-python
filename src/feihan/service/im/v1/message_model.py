# Copyright (c) 2026 上海飞函安全科技有限公司 (Shanghai Feihan Security Technology Co., Ltd.)
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass

from feihan.core.types import BaseModel


# 发送消息（请求）
@dataclass
class SendMessageReq(BaseModel):
    message_type: str | None = None  # 消息类型
    message_content: MessageContent | None = None  # 消息内容
    chat_id: str | None = None  # 聊天 id
    reply_message_id: str | None = None  # 本条消息回复的消息 id


# 发送消息（响应）
@dataclass
class SendMessageResp(BaseModel):
    message_id: str | None = None  # 消息 id


# 获取消息（请求）
@dataclass
class GetMessageReq(BaseModel):
    message_id: str | None = None  # 消息 id


# 获取消息（响应）
@dataclass
class GetMessageResp(BaseModel):
    message: Message | None = None  # 消息


# 撤回消息（请求）
@dataclass
class RecallMessageReq(BaseModel):
    message_id: str | None = None  # 消息 id


# 撤回消息（响应）
@dataclass
class RecallMessageResp(BaseModel):
    pass


# 阅读消息（请求）
@dataclass
class ReadMessageReq(BaseModel):
    message_id: str | None = None  # 消息 id


# 阅读消息（响应）
@dataclass
class ReadMessageResp(BaseModel):
    pass


# 消息内容
@dataclass
class MessageContent(BaseModel):
    text: MessageText | None = None  # 文本消息
    image: MessageImage | None = None  # 图片消息
    sticker: MessageSticker | None = None  # 表情包消息
    video: MessageVideo | None = None  # 视频消息
    audio: MessageAudio | None = None  # 语音消息
    file: MessageFile | None = None  # 文件消息
    user_card: MessageUserCard | None = None  # 个人名片消息
    group_card: MessageGroupCard | None = None  # 群名片消息
    group_announcement: MessageGroupAnnouncement | None = None  # 群公告
    card: MessageCard | None = None  # 卡片消息


# 文本消息
@dataclass
class MessageText(BaseModel):
    content: str | None = None  # 内容
    attachment_list: list[MessageTextAttachment] | None = None  # 附件列表，在 content 中的格式为 {{attach:id}}
    mention_user_list: list[MessageTextMentionUser] | None = None  # 被@人列表，在 content 中的格式为 {{mention:user_id}}，@所有人的 user_id 为 all
    emoji_list: list[MessageTextEmoji] | None = None  # Emoji 列表，在 content 中的格式为 {{emoji:emoji_id}}


# 附件
@dataclass
class MessageTextAttachment(BaseModel):
    attachment_id: str | None = None  # 附件 id，在 content 中引用，引用格式为 {{id}}，客户端自定义
    attachment_type: str | None = None  # 附件类型
    attachment_content: MessageTextAttachmentContent | None = None  # 附件内容


# 附件内容
@dataclass
class MessageTextAttachmentContent(BaseModel):
    image: FileImage | None = None  # 图片


# 图片文件
@dataclass
class FileImage(BaseModel):
    image: File | None = None  # 大图，宽高最大 1024
    image_width: int | None = None  # 图片宽度
    image_height: int | None = None  # 图片高度
    image_origin: File | None = None  # 原图
    image_origin_width: int | None = None  # 原图宽度
    image_origin_height: int | None = None  # 原图高度
    image_thumb_bytes: bytes | None = None  # 缩略图数据，宽高最大 40
    image_thumb_mime: str | None = None  # 缩略图文件类型
    image_dominant_color: str | None = None  # 图片主色调，格式为 #ffffff


# 文件
@dataclass
class File(BaseModel):
    file_id: str | None = None  # 文件 id
    file_mime: str | None = None  # 文件类型
    file_size: int | None = None  # 文件大小
    file_encryption: Encryption | None = None  # 文件加密


# 加密项
@dataclass
class Encryption(BaseModel):
    encryption_algorithm: str | None = None  # 加密算法
    encryption_key: bytes | None = None  # 加密密钥
    encrypted_size: int | None = None  # 加密后的大小


# @ 用户
@dataclass
class MessageTextMentionUser(BaseModel):
    user_id: UserId | None = None  # 用户 id
    user_name: str | None = None  # 当时的用户名称
    is_in_chat: bool | None = None  # 当时该用户是否在聊天中


# 用户 id
@dataclass
class UserId(BaseModel):
    user_id: str | None = None  # 用户在飞函里的 id，同一个用户在所有应用中的 user_id 均相同
    union_user_id: str | None = None  # 用户在同一应用组内的 id，同一个用户在相同应用组下的不同应用中的 union_user_id 均相同
    open_user_id: str | None = None  # 用户在应用内的 id，同一个用户在不同应用中的 open_user_id 均不同


# Emoji
@dataclass
class MessageTextEmoji(BaseModel):
    emoji_id: str | None = None  # Emoji id
    emoji_name: str | None = None  # 当时的 Emoji 名称


# 图片消息
@dataclass
class MessageImage(BaseModel):
    image: FileImage | None = None  # 图片


# 表情包消息
@dataclass
class MessageSticker(BaseModel):
    sticker: Sticker | None = None  # 表情包


# 表情包
@dataclass
class Sticker(BaseModel):
    sticker_id: str | None = None  # 表情包 id
    sticker_name: str | None = None  # 表情包名称
    sticker_name_i18n: dict[str, str] | None = None  # 表情包名称国际化
    sticker_image: FileImage | None = None  # 表情包图片


# 视频消息
@dataclass
class MessageVideo(BaseModel):
    video: FileVideo | None = None  # 视频


# 视频文件
@dataclass
class FileVideo(BaseModel):
    video: File | None = None  # 视频
    video_width: int | None = None  # 视频宽度
    video_height: int | None = None  # 视频高度
    video_duration: float | None = None  # 视频时长
    video_preview: FileImage | None = None  # 视频预览图


# 语音消息
@dataclass
class MessageAudio(BaseModel):
    audio: FileAudio | None = None  # 音频


# 音频文件
@dataclass
class FileAudio(BaseModel):
    audio: File | None = None  # 音频
    audio_duration: float | None = None  # 音频时长


# 文件消息
@dataclass
class MessageFile(BaseModel):
    file: File | None = None  # 文件
    filename: str | None = None  # 文件名


# 个人名片消息
@dataclass
class MessageUserCard(BaseModel):
    user_id: UserId | None = None  # 用户 id


# 群名片消息
@dataclass
class MessageGroupCard(BaseModel):
    chat_id: str | None = None  # 聊天 id


# 群公告
@dataclass
class MessageGroupAnnouncement(BaseModel):
    message_text: MessageText | None = None  # 公告内容


# 卡片消息
@dataclass
class MessageCard(BaseModel):
    schema: str | None = None  # 卡片版本
    v1: MessageCardV1 | None = None  # v1 版本


# v1 版本
@dataclass
class MessageCardV1(BaseModel):
    header: MessageCardV1Header | None = None  # 卡片标题
    body: MessageCardV1Body | None = None  # 卡片正文
    footer: MessageCardV1Footer | None = None  # 卡片底部


# 卡片标题
@dataclass
class MessageCardV1Header(BaseModel):
    title: str | None = None  # 标题文本
    title_i18n: dict[str, str] | None = None  # 标题文本国际化
    template: str | None = None  # 标题颜色模板


# 卡片正文
@dataclass
class MessageCardV1Body(BaseModel):
    message_text: MessageText | None = None  # 卡片正文文本消息
    message_text_i18n: dict[str, MessageText] | None = None  # 卡片正文文本消息国际化


# 卡片底部
@dataclass
class MessageCardV1Footer(BaseModel):
    button_list: list[MessageCardV1Button] | None = None  # 按钮列表
    button_align: str | None = None  # 按钮排版


# 卡片按钮
@dataclass
class MessageCardV1Button(BaseModel):
    button_text: str | None = None  # 按钮文本
    button_text_i18n: dict[str, str] | None = None  # 按钮文本国际化
    template: str | None = None  # 按钮样式模板，取值 default, primary, danger, primary_text, danger_text, primary_filled, danger_filled
    link: MessageCardV1ButtonLink | None = None  # 按钮跳转链接


# 跳转链接
@dataclass
class MessageCardV1ButtonLink(BaseModel):
    url: str | None = None  # 默认链接地址
    android_url: str | None = None  # 安卓链接地址
    ios_url: str | None = None  # ios 链接地址
    pc_url: str | None = None  # 桌面端链接地址


# 消息
@dataclass
class Message(BaseModel):
    message_id: str | None = None  # 消息 id
    message_type: str | None = None  # 消息类型
    message_status: str | None = None  # 消息状态
    message_content: MessageContent | None = None  # 消息内容
    message_created_at: int | None = None  # 消息创建时间（毫秒）
    chat_id: str | None = None  # 聊天 id
    chat_seq_id: int | None = None  # 服务端生成的聊天级别的消息趋势递增 id，用于单链排序
    sender_id: UserId | None = None  # 发送者 id
    reply: MessagePropReply | None = None  # 回复属性


# 消息回复属性
@dataclass
class MessagePropReply(BaseModel):
    reply_message_id: str | None = None  # 本条消息回复的消息 id


# 接收消息
@dataclass
class EventMessageReceiveBody(BaseModel):
    message: Message | None = None  # 消息

