from openai import OpenAI
import os
from app_logger.base_logger import logger
import json
import re
base_url = os.environ.get("BASE_URL")
model = os.environ.get("MODEL")
api_key = os.getenv('OPENROUTER_API_KEY')

def get_ai_response(user_input, price):

    client = OpenAI(
        base_url=base_url,
        api_key=api_key,
    )
    # Personality
    conversation = [
        {
            "role": "system",
            "content": """You are helping me to find a house. Criteria:
            - For 2 people (at least 2 rooms), the price must be at most €750 per person.
            - If price per person exceeds €750, consider adding a third person; then the price per person must be at most €700 (3 rooms).

            Always reply with JSON:
            {
                "decision": true/false,
                "reason": "brief explanation here"
            }
            """,
        },
    ]
    user_input = f"{user_input}, The price is {price}"
    logger.info(user_input)
    conversation.append({"role": "user", "content": user_input})
    response = client.chat.completions.create(
        model=model,
        messages=conversation,
    )
    logger.info(response.choices[0].message.content)
    try:
        json_content = re.sub(r'```(?:json)?\s*|\s*```', '', response.choices[0].message.content).strip()
        response_json = json.loads(json_content)
        decision = response_json["decision"]  # True or False
        reason = response_json["reason"]
    except json.JSONDecodeError:
        logger.error("AI response is not valid JSON")
        decision = None  # or handle differently
    return decision, reason