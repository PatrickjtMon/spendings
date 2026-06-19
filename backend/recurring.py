import json
import os
import uuid

from validators import ALLOWED_CATEGORIES


RECURRING_EXPENSES_FILE = "recurring_expenses.json"


def load_recurring_expenses():
    if not os.path.exists(RECURRING_EXPENSES_FILE):
        return []

    with open(RECURRING_EXPENSES_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_recurring_expenses(recurring_expenses):
    with open(RECURRING_EXPENSES_FILE, "w", encoding="utf-8") as file:
        json.dump(recurring_expenses, file, indent=2, ensure_ascii=False)


def add_recurring_expense(name: str, amount: float, category: str):
    if category not in ALLOWED_CATEGORIES:
        print(f"Invalid category: {category}")
        print(f"Allowed categories: {', '.join(sorted(ALLOWED_CATEGORIES))}")
        return

    recurring_expense = {
        "id": f"rec_{uuid.uuid4().hex[:12]}",
        "name": name,
        "amount": -abs(amount),
        "currency": "EUR",
        "category": category,
        "frequency": "monthly",
        "active": True,
    }

    recurring_expenses = load_recurring_expenses()
    recurring_expenses.append(recurring_expense)
    save_recurring_expenses(recurring_expenses)

    print("Recurring expense added:")
    print(json.dumps(recurring_expense, indent=2, ensure_ascii=False))


def show_recurring_expenses():
    recurring_expenses = load_recurring_expenses()

    if not recurring_expenses:
        print("No recurring expenses saved yet.")
        return

    print("\nRecurring expenses:")

    for index, expense in enumerate(recurring_expenses, start=1):
        status = "active" if expense.get("active") else "inactive"

        print(
            f"{index}. {expense['id']} | "
            f"{expense['name']} | "
            f"{expense['category']} | "
            f"€{abs(expense['amount']):.2f} | "
            f"{expense['frequency']} | "
            f"{status}"
        )

    print()


def delete_recurring_expense(recurring_id: str):
    recurring_expenses = load_recurring_expenses()

    expense_to_delete = None

    for expense in recurring_expenses:
        if expense["id"] == recurring_id:
            expense_to_delete = expense
            break

    if expense_to_delete is None:
        print("Recurring expense not found.")
        return

    recurring_expenses.remove(expense_to_delete)
    save_recurring_expenses(recurring_expenses)

    print("Deleted recurring expense:")
    print(json.dumps(expense_to_delete, indent=2, ensure_ascii=False))


def transaction_matches_recurring(transaction, recurring_expense):
    recurring_name = recurring_expense["name"].lower()
    transaction_description = transaction.get("description", "") or ""
    transaction_merchant = transaction.get("merchant", "") or ""

    transaction_text = f"{transaction_description} {transaction_merchant}".lower()

    recurring_amount = abs(recurring_expense["amount"])
    transaction_amount = abs(transaction["amount"])

    amount_matches = abs(transaction_amount - recurring_amount) <= 1
    name_matches = recurring_name in transaction_text
    category_matches = transaction["category"] == recurring_expense["category"]

    return amount_matches and name_matches and category_matches


def get_recurring_status_for_month(month: str, transactions):
    recurring_expenses = load_recurring_expenses()

    active_recurring_expenses = [
        expense
        for expense in recurring_expenses
        if expense.get("active", True)
    ]

    status_list = []

    for recurring_expense in active_recurring_expenses:
        matching_transaction = None

        for transaction in transactions:
            if transaction_matches_recurring(transaction, recurring_expense):
                matching_transaction = transaction
                break

        if matching_transaction:
            status = "paid"
        else:
            status = "unpaid"

        status_list.append({
            "id": recurring_expense["id"],
            "name": recurring_expense["name"],
            "amount": recurring_expense["amount"],
            "category": recurring_expense["category"],
            "status": status,
            "matching_transaction_id": matching_transaction.get("id") if matching_transaction else None,
        })

    return status_list