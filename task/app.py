import asyncio

# from task.clients.client import DialClient
from task.clients.custom_client import DialClient
from task.constants import DEFAULT_SYSTEM_PROMPT
from task.models.conversation import Conversation
from task.models.message import Message
from task.models.role import Role

async def start(stream: bool) -> None:
    """Main function to start the chat application.

        It will create a conversation loop where user can input messages and get responses from DIAL API using DialClient.
        If stream is True, it will use streaming method to get responses, otherwise it will use regular method.
    """
    dial_client = DialClient("gpt-4")
    should_exit = False

    conversation = Conversation()
    conversation.add_message(Message(role=Role.SYSTEM, content=DEFAULT_SYSTEM_PROMPT))
    while not should_exit:
        user_input = input("Enter a message: ")
        if user_input.lower() == "/exit":
            should_exit = True
            continue

        if not user_input.strip():
            print("Empty message, please enter something.")
            continue

        conversation.add_message(Message(role=Role.USER, content=user_input))

        response_message = None
        if stream:
            response_message = await dial_client.stream_completion(conversation.messages)
        else:
            response_message = dial_client.get_completion(conversation.messages)

        if response_message:
            conversation.add_message(response_message)

asyncio.run(
    start(stream=True)
)
