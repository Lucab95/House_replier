from openai import OpenAI
import os
from app_logger.base_logger import logger
import json
import re

def get_ai_response(user_input, price, client):
    model = os.environ.get("MODEL", "x-ai/grok-4-fast:free")

    # Personality
    conversation = [
        {
            "role": "system",
            "content": """You are helping me to find a house to rent. Criteria:
            - The house is not for student
            - The house is not for short term (less than 12 months)

            Always reply with JSON:
            {
                "decision": true/false,
                "reason": "brief explanation here"
            }
            """,
        },
    ]
    user_input = f"{user_input}, The price is {price}"
    conversation.append({"role": "user", "content": user_input})
    response = client.chat.completions.create(
        model=model,
        messages=conversation,
    )
    decision = False
    reason = None
    try:
        json_content = re.sub(r'```(?:json)?\s*|\s*```', '', response.choices[0].message.content).strip()
        response_json = json.loads(json_content)
        decision = response_json["decision"]  # True or False
        reason = response_json["reason"]
    except json.JSONDecodeError:
        logger.error("AI response is not valid JSON")
    return decision, reason