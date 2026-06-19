import os
import json

DATA_FILE = "transactions.json"
CATEGORY_BUDGETS_FILE = "category_budgets.json"


def load_saved_transactions():
    if not os.path.exists(DATA_FILE):
        return []

    with open(DATA_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_all_transactions(transactions):
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(transactions, file, indent=2, ensure_ascii=False)


def save_transactions(transactions):
    saved_transactions = load_saved_transactions()
    saved_transactions.extend(transactions)
    save_all_transactions(saved_transactions)

def load_category_budgets():
    if not os.path.exists(CATEGORY_BUDGETS_FILE):
        return {}

    with open(CATEGORY_BUDGETS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_category_budgets(category_budgets):
    with open(CATEGORY_BUDGETS_FILE, "w", encoding="utf-8") as file:
        json.dump(category_budgets, file, indent=2, ensure_ascii=False)