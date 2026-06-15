import os
from dotenv import load_dotenv
from anthropic import Anthropic
import re
import json
import uuid

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
INSIGHTS_PROMPT = """
You are an AI personal finance assistant.

Your job is to analyze a monthly financial summary and generate useful insights.

Rules:
- Do not invent numbers.
- Use only the data provided.
- Be practical and specific.
- Mention budget status.
- Mention category spending.
- Mention possible risks or savings opportunities.
- Keep the response concise.
- Return plain text, not JSON.
""" 
ADVICE_PROMPT = """
You are an AI personal finance coach.

Your job is to give practical advice based on the user's monthly financial summary.

Rules:
- Do not invent numbers.
- Use only the data provided.
- Be specific and actionable.
- Focus on budget control, savings, and spending habits.
- Do not give investment advice.
- Do not shame the user.
- Keep the response concise.
- Return plain text, not JSON.
"""
QA_PROMPT = """
You are an AI personal finance assistant.

Answer the user's question using only the provided monthly financial data.

Rules:
- Do not invent numbers.
- If the data is missing, say what is missing.
- Be specific and practical.
- Do not give investment advice.
- Keep the answer concise.
- Return plain text, not JSON.
"""

ANOMALY_PROMPT = """
You are an AI personal finance analyst.

Your job is to detect unusual or risky patterns in the user's monthly financial data.

Rules:
- Use only the data provided.
- Do not invent numbers.
- Always use EUR (€) as the currency symbol.
- Do not use USD ($).
- Focus only on anomalies, risks, unusual patterns, budget risks, high category spending, and transactions that need review.
- If nothing unusual is found, say that clearly.
- If the month has very few transactions, mention that the analysis may be incomplete.
- Be concise and practical.
- Do not use Markdown headings.
- Do not use bold text.
- Return plain text, not JSON.
"""

RECATEGORIZE_PROMPT = """
You are an AI financial transaction categorization assistant.

Review the provided transactions and suggest better categories when needed.

Rules:
- Return ONLY raw JSON.
- Do not use Markdown.
- Do not add explanations outside the JSON.
- Do not invent transactions.
- Do not remove transactions.
- Do not change amounts, dates, merchants, descriptions, currency, type, confidence, or needs_review.
- Only suggest a new category if the current category is clearly wrong.
- Use only the allowed categories.

Allowed categories:
Income, Housing, Groceries, Restaurants, Transport, Subscriptions, Health, Shopping, Entertainment, Savings, Transfers, Other.

Return an array of suggestions with:
- id
- description
- current_category
- suggested_category
- should_change
- reason
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

CATEGORY_BUDGETS_FILE = "category_budgets.json"

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
    category_budgets = load_category_budgets()

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

    month_category_budgets = category_budgets.get(month, {})

    for category, total in data["categories"].items():
        category_budget = month_category_budgets.get(category)

        if category_budget is not None:
            remaining = category_budget - total

            if remaining < 0:
                print(
                    f"- {category}: €{total:.2f} / €{category_budget:.2f} "
                    f"(over by €{abs(remaining):.2f})"
                )
            else:
                print(
                    f"- {category}: €{total:.2f} / €{category_budget:.2f} "
                    f"(remaining €{remaining:.2f})"
                )
        else:
            print(f"- {category}: €{total:.2f} / no category budget")

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


def load_category_budgets():
    if not os.path.exists(CATEGORY_BUDGETS_FILE):
        return {}

    with open(CATEGORY_BUDGETS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_category_budgets(category_budgets):
    with open(CATEGORY_BUDGETS_FILE, "w", encoding="utf-8") as file:
        json.dump(category_budgets, file, indent=2, ensure_ascii=False)


def set_category_budget(month: str, category: str, amount: float):
    if category not in ALLOWED_CATEGORIES:
        print(f"Invalid category: {category}")
        return

    category_budgets = load_category_budgets()

    if month not in category_budgets:
        category_budgets[month] = {}

    category_budgets[month][category] = amount

    save_category_budgets(category_budgets)

    print(f"Budget for {category} in {month} set to €{amount:.2f}")

def show_help():
    print("""
Available commands:

Expense input:
  chocolate 10
  spent 12 euros on Uber
  paid 25 at Continente

Budget commands:
  budget MM-YYYY amount
  category-budget MM-YYYY Category amount

Summary commands:
  summary
  summary MM-YYYY

Other:
  help
  exit
""")
    
def show_transactions(month_filter=None):
    transactions = load_saved_transactions()

    if not transactions:
        print("No transactions saved yet.")
        return

    filtered_transactions = []

    for transaction in transactions:
        transaction_month = get_transaction_month(transaction["date"])

        if month_filter and transaction_month != month_filter:
            continue

        filtered_transactions.append(transaction)

    if not filtered_transactions:
        print("No transactions found.")
        return

    print("\nSaved transactions:")

    for index, transaction in enumerate(filtered_transactions, start=1):
        print(
            f"{index}. {transaction['date']} | "
            f"{transaction['description']} | "
            f"{transaction['category']} | "
            f"€{transaction['amount']:.2f}"
        )

    print()

def delete_transaction(transaction_id: str):
    transactions = load_saved_transactions()

    if not transactions:
        print("No transactions saved yet.")
        return

    transaction_to_delete = None

    for transaction in transactions:
        if transaction.get("id") == transaction_id:
            transaction_to_delete = transaction
            break

    if transaction_to_delete is None:
        print("Transaction not found.")
        return

    transactions.remove(transaction_to_delete)

    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(transactions, file, indent=2, ensure_ascii=False)

    print("Deleted transaction:")
    print(json.dumps(transaction_to_delete, indent=2, ensure_ascii=False))

def generate_unique_transaction_id(existing_ids):
    while True:
        transaction_id = f"tx_{uuid.uuid4().hex[:12]}"

        if transaction_id not in existing_ids:
            return transaction_id


def add_transaction_ids(transactions):
    saved_transactions = load_saved_transactions()
    existing_ids = {transaction.get("id") for transaction in saved_transactions}

    for transaction in transactions:
        if "id" not in transaction:
            transaction["id"] = generate_unique_transaction_id(existing_ids)
            existing_ids.add(transaction["id"])

    return transactions

def edit_transaction(transaction_id: str, field: str, new_value: str):
    transactions = load_saved_transactions()

    allowed_fields = {
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

    if field not in allowed_fields:
        print(f"Invalid field. Allowed fields: {', '.join(sorted(allowed_fields))}")
        return

    for transaction in transactions:
        if transaction.get("id") == transaction_id:
            if field == "amount":
                new_value = float(new_value)

            if field == "confidence":
                new_value = float(new_value)

            if field == "needs_review":
                new_value = new_value.lower() in ["true", "yes", "y"]

            if field == "merchant" and new_value.lower() in ["none", "null"]:
                new_value = None
            if field == "date":
                if not is_valid_date(new_value):
                    print("Invalid date. Use DD-MM-YYYY.")
                    return

            if field == "category":
                if new_value not in ALLOWED_CATEGORIES:
                    print(f"Invalid category. Allowed categories: {', '.join(sorted(ALLOWED_CATEGORIES))}")
                    return

            if field == "type":
                if new_value not in ALLOWED_TYPES:
                    print(f"Invalid type. Allowed types: {', '.join(sorted(ALLOWED_TYPES))}")
                    return

            if field == "amount":
                try:
                    new_value = float(new_value)
                except ValueError:
                    print("Invalid amount. Use a number, for example: -12.50")
                    return

            if field == "confidence":
                try:
                    new_value = float(new_value)
                except ValueError:
                    print("Invalid confidence. Use a number from 0 to 1.")
                    return

                if not 0 <= new_value <= 1:
                    print("Invalid confidence. Use a number from 0 to 1.")
                    return

            transaction[field] = new_value

            with open(DATA_FILE, "w", encoding="utf-8") as file:
                json.dump(transactions, file, indent=2, ensure_ascii=False)

            print("Updated transaction:")
            print(json.dumps(transaction, indent=2, ensure_ascii=False))
            return

    print("Transaction not found.")

def is_valid_date(date: str) -> bool:
    pattern = r"^(0[1-9]|[12][0-9]|3[01])-(0[1-9]|1[0-2])-\d{4}$"
    return bool(re.match(pattern, date))

def view_transaction(transaction_id: str):
    transactions = load_saved_transactions()

    for transaction in transactions:
        if transaction.get("id") == transaction_id:
            print("\nTransaction details:")
            print(json.dumps(transaction, indent=2, ensure_ascii=False))
            return

    print("Transaction not found.")

def build_monthly_summary_data(month: str):
    transactions = load_saved_transactions()
    budgets = load_budgets()
    category_budgets = load_category_budgets()

    month_transactions = []

    needs_review_transactions = []

    total_income = 0
    total_spent = 0
    category_totals = {}

    for transaction in transactions:
        transaction_month = get_transaction_month(transaction["date"])

        if transaction_month != month:
            continue

        if transaction.get("needs_review"):
            needs_review_transactions.append(transaction)

        month_transactions.append(transaction)

        amount = transaction["amount"]

        if amount < 0:
            expense_amount = abs(amount)
            total_spent += expense_amount

            category = transaction["category"]
            category_totals[category] = category_totals.get(category, 0) + expense_amount

        elif amount > 0:
            total_income += amount

    if not month_transactions:
        return None

    net_balance = total_income - total_spent

    return {
        "month": month,
        "monthly_budget": budgets.get(month),
        "category_budgets": category_budgets.get(month, {}),
        "total_income": total_income,
        "total_spent": total_spent,
        "net_balance": net_balance,
        "category_totals": category_totals,
        "transaction_count": len(month_transactions),
        "needs_review_transactions": needs_review_transactions,
    }

def generate_monthly_insights(month: str):
    summary_data = build_monthly_summary_data(month)

    if summary_data is None:
        print("No transactions found for that month.")
        return

    response = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL"),
        max_tokens=500,
        system=INSIGHTS_PROMPT,
        messages=[
            {
                "role": "user",
                "content": json.dumps(summary_data, indent=2, ensure_ascii=False)
            }
        ]
    )

    print(f"\nAI Insights for {month}:")
    print(response.content[0].text)
    print()

def generate_monthly_advice(month: str):
    summary_data = build_monthly_summary_data(month)

    if summary_data is None:
        print("No transactions found for that month.")
        return

    response = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL"),
        max_tokens=500,
        system=ADVICE_PROMPT,
        messages=[
            {
                "role": "user",
                "content": json.dumps(summary_data, indent=2, ensure_ascii=False)
            }
        ]
    )

    print(f"\nAI Advice for {month}:")
    print(response.content[0].text)
    print()

def ask_monthly_question(month: str, question: str):
    summary_data = build_monthly_summary_data(month)

    if summary_data is None:
        print("No transactions found for that month.")
        return

    user_content = {
        "monthly_data": summary_data,
        "question": question
    }

    response = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL"),
        max_tokens=500,
        system=QA_PROMPT,
        messages=[
            {
                "role": "user",
                "content": json.dumps(user_content, indent=2, ensure_ascii=False)
            }
        ]
    )

    print(f"\nAI Answer for {month}:")
    print(response.content[0].text)
    print()

def detect_monthly_anomalies(month: str):
    summary_data = build_monthly_summary_data(month)

    if summary_data is None:
        print("No transactions found for that month.")
        return

    response = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL"),
        max_tokens=500,
        system=ANOMALY_PROMPT,
        messages=[
            {
                "role": "user",
                "content": json.dumps(summary_data, indent=2, ensure_ascii=False)
            }
        ]
    )

    print(f"\nAI Anomalies for {month}:")
    print(response.content[0].text)
    print()

def recategorize_month(month: str):
    transactions = load_saved_transactions()

    month_transactions = [
        transaction
        for transaction in transactions
        if get_transaction_month(transaction["date"]) == month
    ]

    if not month_transactions:
        print("No transactions found for that month.")
        return

    transactions_for_ai = [
        {
            "id": transaction.get("id"),
            "description": transaction["description"],
            "merchant": transaction["merchant"],
            "amount": transaction["amount"],
            "current_category": transaction["category"],
            "type": transaction["type"],
        }
        for transaction in month_transactions
    ]

    response = client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL"),
        max_tokens=1000,
        system=RECATEGORIZE_PROMPT,
        messages=[
            {
                "role": "user",
                "content": json.dumps(transactions_for_ai, indent=2, ensure_ascii=False),
            }
        ],
    )

    suggestions = parse_llm_json(response.content[0].text)

    if suggestions is None:
        return

    if not isinstance(suggestions, list):
        print("Invalid AI response: expected a list.")
        return

    changes_to_apply = []

    for suggestion in suggestions:
        if not suggestion.get("should_change"):
            continue

        transaction_id = suggestion.get("id")
        current_category = suggestion.get("current_category")
        suggested_category = suggestion.get("suggested_category")
        description = suggestion.get("description")
        reason = suggestion.get("reason")

        if suggested_category not in ALLOWED_CATEGORIES:
            print(f"Skipped invalid category: {suggested_category}")
            continue

        print("\nSuggested category change:")
        print(f"ID: {transaction_id}")
        print(f"Description: {description}")
        print(f"Current category: {current_category}")
        print(f"Suggested category: {suggested_category}")
        print(f"Reason: {reason}")

        answer = input("Apply this change? (y/n): ").strip().lower()

        if answer in ["y", "yes"]:
            changes_to_apply.append((transaction_id, suggested_category))

    if not changes_to_apply:
        print("No category changes applied.")
        return

    for transaction in transactions:
        for transaction_id, suggested_category in changes_to_apply:
            if transaction.get("id") == transaction_id:
                transaction["category"] = suggested_category

    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(transactions, file, indent=2, ensure_ascii=False)

    print("Category changes applied.")

while True:
    user_input = input("Describe your spending: ").strip()

    if user_input.lower() in ["exit", "quit"]:
        break
    
    if user_input.lower() == "help":
        show_help()
        continue
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

    if user_input.lower().startswith("category-budget "):
        parts = user_input.split()

        if len(parts) != 4:
            print("Use: category-budget MM-YYYY Category amount")
            continue

        month = parts[1]
        category = parts[2]
        amount = float(parts[3])

        set_category_budget(month, category, amount)
        continue

    if user_input.lower() == "transactions":
        show_transactions()
        continue

    if user_input.lower().startswith("transactions "):
        month = user_input.split(" ", 1)[1]
        show_transactions(month)
        continue
    
    if user_input.lower().startswith("delete "):
        parts = user_input.split()

        if len(parts) != 2:
            print("Use: delete transaction_id")
            continue

        transaction_id = parts[1]

        delete_transaction(transaction_id)
        continue

    if user_input.lower().startswith("edit "):
        parts = user_input.split(" ", 3)

        if len(parts) != 4:
            print("Use: edit transaction_id field new_value")
            continue

        transaction_id = parts[1]
        field = parts[2]
        new_value = parts[3]

        edit_transaction(transaction_id, field, new_value)
        continue

    if user_input.lower().startswith("view "):
        parts = user_input.split()

        if len(parts) != 2:
            print("Use: view transaction_id")
            continue

        transaction_id = parts[1]
        view_transaction(transaction_id)
        continue

    if user_input.lower().startswith("insights "):
        parts = user_input.split()

        if len(parts) != 2:
            print("Use: insights MM-YYYY")
            continue

        month = parts[1]
        generate_monthly_insights(month)
        continue
    
    if user_input.lower().startswith("advice "):
        parts = user_input.split()

        if len(parts) != 2:
            print("Use: advice MM-YYYY")
            continue

        month = parts[1]
        generate_monthly_advice(month)
        continue

    if user_input.lower().startswith("ask "):
        parts = user_input.split(" ", 2)

        if len(parts) != 3:
            print("Use: ask MM-YYYY your question")
            continue

        month = parts[1]
        question = parts[2]

        ask_monthly_question(month, question)
        continue

    if user_input.lower().startswith("anomalies "):
        parts = user_input.split()

        if len(parts) != 2:
            print("Use: anomalies MM-YYYY")
            continue

        month = parts[1]
        detect_monthly_anomalies(month)
        continue

    if user_input.lower().startswith("recategorize "):
        parts = user_input.split()

        if len(parts) != 2:
            print("Use: recategorize MM-YYYY")
            continue

        month = parts[1]
        recategorize_month(month)
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

    confirmed_transactions = add_transaction_ids(confirmed_transactions)

    save_transactions(confirmed_transactions)

    print("\nSaved transactions:")
    print(json.dumps(confirmed_transactions, indent=2, ensure_ascii=False))