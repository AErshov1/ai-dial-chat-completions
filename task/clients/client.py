import os

from aidial_client import Dial, AsyncDial

from task.clients.base import BaseClient
from task.constants import DIAL_ENDPOINT, DIAL_API_KEY, APP_DEBUG
from task.models.message import Message
from task.models.role import Role

class DialClient(BaseClient):

    def __init__(self, deployment_name: str):
        super().__init__(deployment_name)
        self.dial_client = Dial(api_key=DIAL_API_KEY, base_url=DIAL_ENDPOINT)
        self.async_dial_client = AsyncDial(api_key=DIAL_API_KEY, base_url=DIAL_ENDPOINT)

    def get_completion(self, messages: list[Message]) -> Message:
        completion = self.dial_client.chat.completions.create(
            deployment_name=self._deployment_name,
            stream=False,
            messages=[
                msg.to_dict() for msg in messages
            ],
            api_version="2023-12-01-preview"
        )
        if not completion or not completion.choices:
            raise Exception("No choices in response found")

        resp_msg = completion.choices[0].message
        if APP_DEBUG:
          print("[DialClient] Completion Response:", completion)

        print(f"Assistant: {resp_msg.content}")

        return Message(
            role=Role.AI,
            content=resp_msg.content
        )

    async def stream_completion(self, messages: list[Message]) -> Message:
        completion = await self.async_dial_client.chat.completions.create(
            deployment_name=self._deployment_name,
            stream=True,
            messages=[
                msg.to_dict() for msg in messages
            ],
            api_version="2023-12-01-preview"
        )

        contents = []
        header_printed = False
        async for chunk in completion:
            if not chunk.choices:
                continue

            if APP_DEBUG:
                print("[DialClient] Streamed Chunk:", chunk)

            chunk_msg = chunk.choices[0].delta.content
            if not header_printed:
                print("Assistant (streaming): ", end="", flush=True)
                header_printed = True

            if chunk_msg:
                print(chunk_msg, end="", flush=True)
                contents.append(chunk_msg)

        print()  # Print new line after streaming is done
        return Message(
            role=Role.AI,
            content="".join(contents)
        )
