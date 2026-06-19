import os
import json
from dotenv import load_dotenv
from anthropic import Anthropic

from prompts import (
    SYSTEM_PROMPT,
    INSIGHTS_PROMPT,
    ADVICE_PROMPT,
    QA_PROMPT,
    ANOMALY_PROMPT,
    RECATEGORIZE_PROMPT,
)

load_dotenv()

client = Anthropic(
    api_key=os.getenv("ANTHROPIC_API_KEY")
)


def call_anthropic(system_prompt: str, content: str, max_tokens: int = 500):
    response = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL"),
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[
            {"role": "user", "content": content}
        ]
    )

    return response.content[0].text


def analyze_text(text: str):
    return call_anthropic(
        system_prompt=SYSTEM_PROMPT,
        content=text,
        max_tokens=500,
    )


def generate_insights_response(summary_data):
    return call_anthropic(
        system_prompt=INSIGHTS_PROMPT,
        content=json.dumps(summary_data, indent=2, ensure_ascii=False),
        max_tokens=500,
    )


def generate_advice_response(summary_data):
    return call_anthropic(
        system_prompt=ADVICE_PROMPT,
        content=json.dumps(summary_data, indent=2, ensure_ascii=False),
        max_tokens=500,
    )


def answer_monthly_question_response(summary_data, question: str):
    content = {
        "monthly_data": summary_data,
        "question": question,
    }

    return call_anthropic(
        system_prompt=QA_PROMPT,
        content=json.dumps(content, indent=2, ensure_ascii=False),
        max_tokens=500,
    )


def detect_anomalies_response(summary_data):
    return call_anthropic(
        system_prompt=ANOMALY_PROMPT,
        content=json.dumps(summary_data, indent=2, ensure_ascii=False),
        max_tokens=500,
    )


def recategorize_response(transactions_for_ai):
    return call_anthropic(
        system_prompt=RECATEGORIZE_PROMPT,
        content=json.dumps(transactions_for_ai, indent=2, ensure_ascii=False),
        max_tokens=1000,
    )