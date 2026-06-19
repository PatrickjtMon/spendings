import json

from storage import (
    load_saved_transactions,
    load_category_budgets,
    save_all_transactions,
)
from transactions import get_transaction_month
from validators import ALLOWED_CATEGORIES
from json_utils import parse_llm_json
from ai import (
    generate_insights_response,
    generate_advice_response,
    answer_monthly_question_response,
    detect_anomalies_response,
    recategorize_response,
)


def build_monthly_summary_data(month: str):
    transactions = load_saved_transactions()
    category_budgets = load_category_budgets()

    month_transactions = []
    needs_review_transactions = []

    total_income = 0
    total_expenses = 0
    total_savings = 0
    category_totals = {}

    for transaction in transactions:
        transaction_month = get_transaction_month(transaction["date"])

        if transaction_month != month:
            continue

        month_transactions.append(transaction)

        if transaction.get("needs_review"):
            needs_review_transactions.append(transaction)

        amount = transaction["amount"]
        category = transaction["category"]
        transaction_type = transaction["type"]

        if amount > 0 and transaction_type == "income":
            total_income += amount

        elif amount < 0:
            expense_amount = abs(amount)

            if category == "Savings":
                total_savings += expense_amount
            else:
                total_expenses += expense_amount

            category_totals[category] = category_totals.get(category, 0) + expense_amount

    if not month_transactions:
        return None

    monthly_budget = total_income
    total_outflow = total_expenses + total_savings
    remaining = monthly_budget - total_outflow

    if monthly_budget > 0:
        savings_rate = total_savings / monthly_budget
    else:
        savings_rate = 0

    return {
        "month": month,
        "monthly_budget": monthly_budget,
        "budget_source": "income",
        "total_income": total_income,
        "total_expenses": total_expenses,
        "total_savings": total_savings,
        "total_outflow": total_outflow,
        "remaining": remaining,
        "savings_rate": savings_rate,
        "category_budgets": category_budgets.get(month, {}),
        "category_totals": category_totals,
        "transaction_count": len(month_transactions),
        "needs_review_transactions": needs_review_transactions,
    }

def generate_monthly_insights(month: str):
    summary_data = build_monthly_summary_data(month)

    if summary_data is None:
        print("No transactions found for that month.")
        return

    response_text = generate_insights_response(summary_data)

    print(f"\nAI Insights for {month}:")
    print(response_text)
    print()


def generate_monthly_advice(month: str):
    summary_data = build_monthly_summary_data(month)

    if summary_data is None:
        print("No transactions found for that month.")
        return

    response_text = generate_advice_response(summary_data)

    print(f"\nAI Advice for {month}:")
    print(response_text)
    print()

def detect_monthly_anomalies(month: str):
    summary_data = build_monthly_summary_data(month)

    if summary_data is None:
        print("No transactions found for that month.")
        return

    response_text = detect_anomalies_response(summary_data)

    print(f"\nAI Anomalies for {month}:")
    print(response_text)
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

    response_text = recategorize_response(transactions_for_ai)
    suggestions = parse_llm_json(response_text)

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

    save_all_transactions(transactions)

    print("Category changes applied.")

def ask_monthly_question(month: str, question: str):
    summary_data = build_monthly_summary_data(month)

    if summary_data is None:
        print("No transactions found for that month.")
        return

    response_text = answer_monthly_question_response(summary_data, question)

    print(f"\nAI Answer for {month}:")
    print(response_text)
    print()

