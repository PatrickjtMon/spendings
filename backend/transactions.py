import json
import uuid

from storage import (
    load_saved_transactions,
    save_all_transactions,
)
from validators import (
    ALLOWED_CATEGORIES,
    ALLOWED_TYPES,
    is_valid_date,
)


def get_transaction_month(date: str) -> str:
    day, month, year = date.split("-")
    return f"{month}-{year}"

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

def review_transactions(transactions):
    confirmed_transactions = []

    for transaction in transactions:
        print("\nTransaction found:")
        print(json.dumps(transaction, indent=2, ensure_ascii=False))

        answer = input("Save this transaction? (y/n): ").strip().lower()

        if answer in ["y", "yes"]:
            confirmed_transactions.append(transaction)
        else:
            print("Transaction skipped.")

    return confirmed_transactions


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
            f"{index}. {transaction.get('id', 'no-id')} | "
            f"{transaction['date']} | "
            f"{transaction['description']} | "
            f"{transaction['category']} | "
            f"€{transaction['amount']:.2f}"
        )

    print()


def view_transaction(transaction_id: str):
    transactions = load_saved_transactions()

    for transaction in transactions:
        if transaction.get("id") == transaction_id:
            print("\nTransaction details:")
            print(json.dumps(transaction, indent=2, ensure_ascii=False))
            return

    print("Transaction not found.")


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
    save_all_transactions(transactions)

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

            if field == "needs_review":
                new_value = new_value.lower() in ["true", "yes", "y"]

            if field == "merchant" and new_value.lower() in ["none", "null"]:
                new_value = None

            transaction[field] = new_value
            save_all_transactions(transactions)

            print("Updated transaction:")
            print(json.dumps(transaction, indent=2, ensure_ascii=False))
            return

    print("Transaction not found.")