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