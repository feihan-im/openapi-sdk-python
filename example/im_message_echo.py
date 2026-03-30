# Copyright (c) 2026 上海飞函安全科技有限公司 (Shanghai Feihan Security Technology Co., Ltd.)
# SPDX-License-Identifier: Apache-2.0

import asyncio

from feihan import (
    FeihanClient,
    CreateTypingReq,
    DeleteTypingReq,
    EventMessageReceive,
    MessageType_CARD,
    ReadMessageReq,
    SendMessageReq,
    MessageContent,
    MessageCard,
    MessageCardV1,
    MessageCardV1Header,
    MessageCardV1Body,
    MessageCardV1Footer,
    MessageCardV1Button,
    MessageCardV1ButtonLink,
    MessageText,
)


async def main() -> None:
    client = await FeihanClient.create(
        "http://localhost:11000",
        "c-TestAppId2",
        "TestAppSecret2",
    )

    def on_message(event: EventMessageReceive) -> None:
        print("Message received:", event.body)

        chat_id = event.body.message.chat_id if event.body.message else ""
        message_id = event.body.message.message_id if event.body.message else ""

        asyncio.ensure_future(handle_message(client, chat_id, message_id))

    async def handle_message(client, chat_id: str, message_id: str) -> None:
        try:
            await client.im.chat.create_typing(CreateTypingReq(chat_id=chat_id))
        except Exception as e:
            print(f"create_typing failed: {e}")

        try:
            await client.im.message.read_message(ReadMessageReq(message_id=message_id))
        except Exception as e:
            print(f"read_message failed: {e}")

        try:
            content = "New version features:\n- Added a Night Mode theme\n- Added multilingual support\n- Fixed the iOS video playback crash issue"
            await client.im.message.send_message(SendMessageReq(
                message_type=MessageType_CARD,
                message_content=MessageContent(
                    card=MessageCard(
                        schema="1.0",
                        v1=MessageCardV1(
                            header=MessageCardV1Header(
                                title="Feihan new version released!",
                                title_i18n={"en": "Feihan new version released!"},
                                template="green",
                            ),
                            body=MessageCardV1Body(
                                message_text=MessageText(content=content),
                                message_text_i18n={"en": MessageText(content=content)},
                            ),
                            footer=MessageCardV1Footer(
                                button_list=[
                                    MessageCardV1Button(button_text="Open website", button_text_i18n={"en": "Jump to official website"}, link=MessageCardV1ButtonLink(url="https://feihanim.cn/"), template=tmpl)
                                    for tmpl in ["default", "primary_filled", "primary", "danger", "danger_filled", "danger_text", "primary_text"]
                                ],
                                button_align="start",
                            ),
                        ),
                    ),
                ),
                chat_id=chat_id,
            ))
        except Exception as e:
            print(f"send_message failed: {e}")

        try:
            await client.im.chat.delete_typing(DeleteTypingReq(chat_id=chat_id))
        except Exception as e:
            print(f"delete_typing failed: {e}")

    client.im.message.event.on_message_receive(on_message)

    # Keep alive for 10 seconds
    await asyncio.sleep(10)
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
