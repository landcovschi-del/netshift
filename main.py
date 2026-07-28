"""Sandbox script: shorten text via the OpenAI API.

Not part of netshift -- netshift needs no API key at all. This is the earlier
experiment, kept because it still works and because of the lesson below.

The key used to be written directly into this file. Never do that: the file
goes into git, into backups, into screenshots, and the key goes with it.
Consider that key compromised and revoke it.

The key now comes from the OPENAI_API_KEY environment variable, which .env
supplies (see .env.example). .env is in .gitignore. In .NET the same job is
done by User Secrets in development and environment variables in production --
appsettings.json with a live key does not get committed, for the same reason.

Run:  uv run --with openai --with python-dotenv python main.py
"""

import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    sys.exit(
        "OPENAI_API_KEY is not set.\n"
        "Copy .env.example to .env and put a fresh key there "
        "(revoke the old one at https://platform.openai.com/api-keys)."
    )

client = OpenAI(api_key=api_key)

while True:
    user_input = input("Text to shorten (or 'exit'): ")

    if user_input.lower() == "exit":
        break

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=f"Make this text shorter and clearer:\n\n{user_input}",
    )

    print("\nResult:\n")
    print(response.output[0].content[0].text)
    print("\n" + "-" * 50 + "\n")
