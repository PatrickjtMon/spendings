import os
from dotenv import load_dotenv
from anthropic import Anthropic
import re
import json

load_dotenv()
client = Anthropic(
    api_key= os.getenv("ANTHROPIC_API_KEY")
)

SYSTEM_PROMPT = """
You are an AI financial transaction parser.

Your job is to extract financial transactions from the user's natural language text.

Return ONLY raw JSON.
Do not use Markdown.
Do not wrap the response in ```json.
Do not add explanations before or after the JSON.
Return an array of transactions.

Each transaction must include:
- date
- description
- merchant
- amount
- currency
- category
- type
- confidence
- needs_review

General rules:
- Do not invent transactions.
- Dates must be in DD-MM-YYYY format.
- If no date is mentioned, use today's date.
- Expenses must be negative amounts.
- Income must be positive amounts.
- Use EUR as default currency.
- Do not use "Unknown" as merchant.
- If the merchant, store, company, or person is not mentioned, set merchant to null.
- Always include a description with what the user bought, paid for, received, or transferred.
- If the item is known but the merchant is missing, still extract the transaction and set needs_review to true.
- If the category is uncertain, set needs_review to true.
- Confidence must be a number from 0 to 1.

Transaction validity rules:
- A valid transaction must include both:
  - a clear monetary amount
  - a description of what was bought, paid, received, or transferred
- Only extract transactions when both fields are present.
- If the amount is missing, unclear, or invalid, return [].
- If the description is missing, unclear, or invalid, return [].
- Never invent missing descriptions or amounts.
- Never use placeholder values like -1, 0, 1, "Unknown", "Transaction", or empty strings.

Allowed categories:
- Income
- Housing
- Groceries
- Restaurants
- Transport
- Subscriptions
- Health
- Shopping
- Entertainment
- Savings
- Transfers
- Other

Allowed types:
- income
- expense
- transfer

Category rules:
- Income: salary, freelance payment, bonus, refund, money received as income.
- Housing: rent, mortgage, electricity, water, gas, internet, utilities, house maintenance.
- Groceries: food, drinks, supermarket items, household essentials, snacks, chocolate, bread, milk, fruit, meat, fish, cleaning products.
- Restaurants: restaurants, cafés, takeaway, delivery food, fast food, meals eaten outside.
- Transport: Uber, Bolt, taxi, bus, train, metro, fuel, parking, tolls.
- Subscriptions: Netflix, Spotify, iCloud, Amazon Prime, recurring digital services.
- Health: pharmacy, doctor, dentist, medicine, healthcare, insurance.
- Shopping: clothes, electronics, books, furniture, cosmetics, accessories, non-food retail purchases.
- Entertainment: cinema, games, concerts, events, hobbies, leisure activities.
- Savings: money moved to savings, investments, emergency fund, deposits into savings accounts.
- Transfers: money sent to or received from another person, MBWay, bank transfers, unclear personal payments.
- Other: use only when no other category fits.

Important classification rules:
- If the user mentions a food item bought for home consumption, classify it as Groceries, not Shopping.
- If the user mentions eating at a restaurant, café, takeaway, or delivery, classify it as Restaurants.
- If the user mentions a supermarket name, classify it as Groceries.
- If the user sends money to a person and does not explain why, classify it as Transfers and set needs_review to true.
- If the transaction purpose is unclear, set needs_review to true.
- If the merchant is missing but the description is clear, do not invent a merchant.

Output format example:
[
  {
    "date": "19-01-2025",
    "description": "Chocolate",
    "merchant": null,
    "amount": -10,
    "currency": "EUR",
    "category": "Groceries",
    "type": "expense",
    "confidence": 0.85,
    "needs_review": true
  }
]
"""

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

DATA_FILE = "transactions.json"

BUDGETS_FILE = "budgets.json"

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

def analyze_text(text):

    responde = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL"),
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": text}
        ]
    )

    return responde.content[0].text



def user_mentioned_money(text: str) -> bool:
    pattern = r"(€\s*\d+([.,]\d+)?|\d+([.,]\d+)?\s*(euros?|eur|€)?$|\d+([.,]\d+)?\s*(euros?|eur|€))"
    return bool(re.search(pattern, text.lower().strip()))

def ask_for_amount() -> str:
    while True:
        amount = input("How much did you spend? ")

        if amount.lower() in ["exit", "quit"]:
            exit()

        if user_mentioned_money(amount):
            return amount

        print("Please enter a valid amount, for example: 10, 10 euros, or €10")

def has_description(text: str) -> bool:
    # Remove money-like parts from the text
    text_without_money = re.sub(
        r"(€\s*\d+([.,]\d+)?|\d+([.,]\d+)?\s*(euros?|euro|eur|€)?)",
        "",
        text.lower()
    ).strip()

    # If there is still meaningful text, we have a description
    return len(text_without_money) >= 3

def clean_llm_output(text: str) -> str:
    return (
        text
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

def parse_llm_json(text: str):
    cleaned_text = clean_llm_output(text)

    try:
        return json.loads(cleaned_text)
    except json.JSONDecodeError:
        print("The AI returned invalid JSON.")
        print(cleaned_text)
        return None
    
def review_transactions(transactions):
    confirmed_transactions = []

    for transaction in transactions:
        print("\nTransaction found:")
        print(json.dumps(transaction, indent=2, ensure_ascii=False))

        answer = input("Save this transaction? (y/n): ").strip().lower()

        if answer == "y" or answer == "yes":
            confirmed_transactions.append(transaction)
        else:
            print("Transaction skipped.")

    return confirmed_transactions

def load_saved_transactions():
    if not os.path.exists(DATA_FILE):
        return []

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_transactions(transactions):
    saved_transactions = load_saved_transactions()
    saved_transactions.extend(transactions)

    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(saved_transactions, file, indent=2, ensure_ascii=False)

def get_transaction_month(date: str) -> str:
    # date format: DD-MM-YYYY
    day, month, year = date.split("-")
    return f"{month}-{year}"

def show_monthly_summary(month_filter=None):
    transactions = load_saved_transactions()
    budgets = load_budgets()

    if not transactions:
        print("No transactions saved yet.")
        return

    monthly_totals = {}

    for transaction in transactions:
        transaction_month = get_transaction_month(transaction["date"])

        if month_filter and transaction_month != month_filter:
            continue

        if transaction["amount"] < 0:
            category = transaction["category"]
            amount = abs(transaction["amount"])

            if transaction_month not in monthly_totals:
                monthly_totals[transaction_month] = {
                    "total_spent": 0,
                    "categories": {}
                }

            monthly_totals[transaction_month]["total_spent"] += amount

            monthly_totals[transaction_month]["categories"][category] = (
                monthly_totals[transaction_month]["categories"].get(category, 0) + amount
            )

    if not monthly_totals:
        print("No transactions found for that month.")
        return
    
    
    for month, data in monthly_totals.items():
        print(f"\nSummary for {month}:")
        budget = budgets.get(month)

        if budget is not None:
            remaining = budget - data["total_spent"]

            print(f"Budget: €{budget:.2f}")
            print(f"Spent: €{data['total_spent']:.2f}")
            print(f"Remaining: €{remaining:.2f}")

            if remaining < 0:
                print(f"Status: Over budget by €{abs(remaining):.2f}")
            else:
                print(f"Status: Under budget by €{remaining:.2f}")
        else:
            print("Budget: not set")
            print(f"Spent: €{data['total_spent']:.2f}")

        print("\nBy category:")
        for category, total in data["categories"].items():
            print(f"- {category}: €{total:.2f}")

        print()

def load_budgets():
    if not os.path.exists(BUDGETS_FILE):
        return {}

    with open(BUDGETS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_budgets(budgets):
    with open(BUDGETS_FILE, "w", encoding="utf-8") as file:
        json.dump(budgets, file, indent=2, ensure_ascii=False)


def set_monthly_budget(month: str, amount: float):
    budgets = load_budgets()
    budgets[month] = amount
    save_budgets(budgets)

    print(f"Budget for {month} set to €{amount:.2f}")


while True:
    user_input = input("Describe your spending: ").strip()

    if user_input.lower() in ["exit", "quit"]:
        break

    if user_input.lower() == "summary":
        show_monthly_summary()
        continue
    
    if user_input.lower().startswith("summary "):
        month = user_input.split(" ", 1)[1]
        show_monthly_summary(month)
        continue

    if user_input.lower().startswith("budget "):
        parts = user_input.split()

        if len(parts) != 3:
            print("Use: budget MM-YYYY amount")
            continue

        month = parts[1]
        amount = float(parts[2])

        set_monthly_budget(month, amount)
        continue

    has_money = user_mentioned_money(user_input)
    has_desc = has_description(user_input)

    if not has_desc:
        description = input("What did you spend it on? ").strip()

        if description.lower() in ["exit", "quit"]:
            break

        user_input = f"{description} {user_input}"

    if not has_money:
        amount = ask_for_amount()
        user_input = f"{user_input} {amount}"

    raw_result = analyze_text(user_input)
    parsed_result = parse_llm_json(raw_result)

    if parsed_result is None:
        continue

    valid_transactions = validate_transactions(parsed_result)

    confirmed_transactions = review_transactions(valid_transactions)

    if not confirmed_transactions:
        print("No transactions confirmed.")
        continue

    save_transactions(confirmed_transactions)

    print("\nSaved transactions:")
    print(json.dumps(confirmed_transactions, indent=2, ensure_ascii=False))