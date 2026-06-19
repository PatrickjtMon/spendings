import json


def clean_llm_output(text: str) -> str:
    text = text.strip()

    if text.startswith("```json"):
        text = text.removeprefix("```json").strip()

    if text.startswith("```"):
        text = text.removeprefix("```").strip()

    if text.endswith("```"):
        text = text.removesuffix("```").strip()

    return text


def parse_llm_json(text: str):
    cleaned_text = clean_llm_output(text)

    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError:
        print("The AI returned invalid JSON.")
        print(cleaned_text)
        return None