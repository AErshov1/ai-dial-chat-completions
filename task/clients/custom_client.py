import json
from typing import Any
import aiohttp
import requests

from task.clients.base import BaseClient
from task.constants import DIAL_ENDPOINT, APP_DEBUG
from task.models.message import Message
from task.models.role import Role


class DialClient(BaseClient):
    _endpoint: str
    _api_key: str

    def __init__(self, deployment_name: str):
        super().__init__(deployment_name)
        self._endpoint = DIAL_ENDPOINT + f"/openai/deployments/{deployment_name}/chat/completions"

    def get_completion(self, messages: list[Message]) -> Message:
        resp = requests.post(
            url=self._endpoint,
            headers={
                "api-key": self._api_key,
                "Content-Type": "application/json"
            },
            json={
                "messages": [msg.to_dict() for msg in messages]
            }
        )
        if resp.status_code != 200:
            raise Exception(f"HTTP {resp.status_code}: {resp.text}")

        if APP_DEBUG:
            print("[CustomDialClient] Completion Response:", resp.text)

        json = resp.json()
        if not json or not json.get("choices"):
            raise Exception("No choices in response found")

        msg = json["choices"][0]["message"]
        content = msg['content']
        print(f"Assistant: {content}")

        return Message(
            role=Role.AI,
            content=content)

    @staticmethod
    def _parse_chunks_content(messages: list[str]) -> tuple[bool, str]:
        content = ""
        end_stream = False
        for chunk_str in messages:
          if APP_DEBUG:
              print(f"[CustomDialClient] Parsing String: =>>{chunk_str}<<=")

          if chunk_str.startswith("data: {") and chunk_str.endswith("}"):
              json_str = chunk_str[len("data: "):]
              try:
                  json_data = json.loads(json_str)
                  choices = json_data.get("choices")
                  if choices and len(choices) > 0:
                      content += choices[0].get("delta", {}).get("content", "")
              except json.JSONDecodeError:
                  if APP_DEBUG:
                      print("[CustomDialClient] Failed to parse JSON from chunk:", json_str)
          elif chunk_str == "data: [DONE]":
              end_stream = True

        return end_stream, content

    @staticmethod
    def _get_chunked_messages(buffer: str) -> tuple[str, list[str]]:
      messages = []
      start_indx = 0
      while True:
          end_idx = buffer.find("\n\n", start_indx)
          if end_idx == -1:
              end_idx = buffer.find("\r\n\r\n", start_indx)
          if end_idx == -1:
              break

          lines =  buffer[:end_idx].splitlines()
          if not lines:
            start_indx = end_idx + 2
            continue

          if lines[0].startswith("data: [DONE]"):
              messages.append(lines[0])
              return "", messages

          if lines[0].startswith("data: {"):
              next_data = buffer[end_idx+2:]

              if next_data.startswith("data: "):
                messages.append(buffer[:end_idx])
                buffer = next_data
                start_indx = 0 # reset index to start of buffer for next message
              else:
                 start_indx = end_idx + 2 # move index to end of current message for next search

      return buffer, messages

    async def stream_completion(self, messages: list[Message], chunk_size: int = 1024) -> Message:
        contents = []
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url=self._endpoint,
                json={
                    "stream": True,
                    "messages": [msg.to_dict() for msg in messages]
                },
                headers={
                    "api-key": self._api_key,
                    "Content-Type": "application/json"
                }
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise Exception(f"HTTP {resp.status}: {text}")

                chunk_buffer = ""
                header_printed = False
                # Process streamed chunks
                async for chunk in resp.content.iter_chunked(chunk_size):
                    chunk_str = chunk.decode('utf-8')
                    chunk_buffer += chunk_str
                    if APP_DEBUG:
                        print("[CustomDialClient] Received Chunk:", chunk_str)

                    chunk_buffer, messages = DialClient._get_chunked_messages(chunk_buffer)
                    if APP_DEBUG:
                        print(f"[CustomDialClient] Extracted Messages: {messages}")

                    stream_end, content = DialClient._parse_chunks_content(messages)
                    if APP_DEBUG:
                        print(f"[CustomDialClient] Parsed Chunk - stream end: {stream_end}, content: '{content}'")

                    if content:
                        if not header_printed:
                            print("Assistant (streaming): ", end="", flush=True)
                            header_printed = True

                        print(content, end="", flush=True)
                        contents.append(content)

                    if stream_end:
                        print()  # Move to next line after stream ends
                        break

        return Message(
            role=Role.AI,
            content="".join(contents)
        )
