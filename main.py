import os
import json

from anthropic import Anthropic
from dotenv import load_dotenv

import tools as tls


load_dotenv()
client = Anthropic(
    base_url="https://openrouter.ai/api",
    auth_token=os.environ["SIMPLE_AGENT_KEY"],  # sent as "Authorization: Bearer ..."
    api_key=None,
)


def run_agent(goal: str, max_steps: int = 10) -> str:
    tool_schemas = [
        {"name": name, "description": t["description"], "input_schema": t["parameters"]}
        for name, t in tls.TOOLS.items()
    ]

    messages = [{"role": "user", "content": goal}]

    for step in range(max_steps):
        print(f"\n--- Step {step + 1} ---")

        response = client.messages.create(
            model="anthropic/claude-haiku-5.5",
            max_tokens=500,
            tools=tool_schemas,
            messages=messages
        )

        # If Claude is done, return the final answer
        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, 'text'):
                    return block.text
            return "Task complete."

        # Otherwise, execute whatever tools Claude requested
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                tool_name = block.name
                tool_input = block.input
                print(f"  Tool call: {tool_name}({tool_input})")

                if tool_name in tls.TOOLS:
                    result = tls.TOOLS[tool_name]["function"](**tool_input)
                else:
                    result = json.dumps({"error": f"Unknown tool: {tool_name}"})

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result
                })

        # Feed the results back so Claude can decide what to do next
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    return "Max steps reached."


def main():
    # goal = "List the files in the current directory, then read the contents of README.md if it exists."
    goal = "List files in the current directory, read README.md, and write a summary to SUMMARY.md."
    result = run_agent(
        goal
    )
    print(f"\nFinal answer:\n{result}")


if __name__ == "__main__":
    main()
