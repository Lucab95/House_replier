import os
import json
import argparse

from dotenv import load_dotenv
from openai import OpenAI

from utils.GPT import get_ai_response


def build_client():
    """Build and return an OpenAI client based on environment variables.

    Required envs:
      - OPENROUTER_API_KEY
      - MODEL
    Optional envs:
      - BASE_URL (for OpenAI-compatible providers)
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set in the environment/.env")

    base_url = os.getenv("BASE_URL")
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(description="Simple AI test for get_ai_response")
    parser.add_argument(
        "--prompt",
        type=str,
        default="I found a studio in Rotterdam near the center. No students, long-term rental only.",
        help="User prompt/description to evaluate",
    )
    parser.add_argument(
        "--price",
        type=int,
        default=1200,
        help="Monthly price to include in the evaluation",
    )

    args = parser.parse_args()

    # Validate model existence early (used inside utils/GPT.py)
    model = os.getenv("MODEL")
    if not model:
        raise RuntimeError("MODEL is not set in the environment/.env (e.g. 'gpt-4o-mini')")

    client = build_client()

    decision, reason = get_ai_response(args.prompt, args.price, client)

    print(json.dumps({
        "decision": bool(decision),
        "reason": reason or "No reason provided by the model"
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
