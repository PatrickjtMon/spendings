import re

ALLOWED_CATEGORIES = {
    "Income",
    "Housing",
    "Groceries",
    "Restaurants",
    "Transport",
    "Subscriptions",
    "Health",
    "Shopping",
    "Entertainment",
    "Savings",
    "Transfers",
    "Other",
}

ALLOWED_TYPES = {
    "income",
    "expense",
    "transfer",
}

REQUIRED_FIELDS = {
    "date",
    "description",
    "merchant",
    "amount",
    "currency",
    "category",
    "type",
    "confidence",
    "needs_review",
}


def validate_transactions(data):
    if not isinstance(data, list):
        print("Invalid response: AI output must be a list.")
        return None

    valid_transactions = []

    for transaction in data:
        if not isinstance(transaction, dict):
            print("Invalid transaction: each item must be an object.")
            continue

        missing_fields = REQUIRED_FIELDS - transaction.keys()

        if missing_fields:
            print(f"Invalid transaction: missing fields {missing_fields}")
            continue

        if not isinstance(transaction["amount"], (int, float)):
            print("Invalid transaction: amount must be a number.")
            continue

        if transaction["category"] not in ALLOWED_CATEGORIES:
            print(f"Invalid transaction: invalid category {transaction['category']}")
            continue

        if transaction["type"] not in ALLOWED_TYPES:
            print(f"Invalid transaction: invalid type {transaction['type']}")
            continue

        if not 0 <= transaction["confidence"] <= 1:
            print("Invalid transaction: confidence must be between 0 and 1.")
            continue

        if not isinstance(transaction["needs_review"], bool):
            print("Invalid transaction: needs_review must be true or false.")
            continue

        valid_transactions.append(transaction)

    return valid_transactions


def user_mentioned_money(text: str) -> bool:
    pattern = r"(€\s*\d+([.,]\d+)?|\d+([.,]\d+)?\s*(euros?|eur|€)?$|\d+([.,]\d+)?\s*(euros?|eur|€))"
    return bool(re.search(pattern, text.lower().strip()))


def has_description(text: str) -> bool:
    text_without_money = re.sub(
        r"(€\s*\d+([.,]\d+)?|\d+([.,]\d+)?\s*(euros?|euro|eur|€)?)",
        "",
        text.lower()
    ).strip()

    return len(text_without_money) >= 3


def is_valid_date(date: str) -> bool:
    pattern = r"^(0[1-9]|[12][0-9]|3[01])-(0[1-9]|1[0-2])-\d{4}$"
    return bool(re.match(pattern, date))