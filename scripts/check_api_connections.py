"""Check API connectivity without printing credentials or private documents."""

import time

from dotenv import load_dotenv
from openai import OpenAI


def main() -> None:
    load_dotenv()
    client = OpenAI(timeout=12, max_retries=0)
    checks = (
        ("models", lambda: client.models.retrieve("gpt-4o-mini")),
        (
            "chat",
            lambda: client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "Reply OK."}],
                max_tokens=8,
            ),
        ),
    )
    for name, check in checks:
        start = time.monotonic()
        try:
            check()
        except Exception as error:
            status = getattr(error, "status_code", None)
            print(
                f"{name}: {type(error).__name__} "
                f"status={status} elapsed={time.monotonic() - start:.1f}s",
                flush=True,
            )
        else:
            print(f"{name}: OK elapsed={time.monotonic() - start:.1f}s", flush=True)


if __name__ == "__main__":
    main()
