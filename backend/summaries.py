from storage import (
    load_saved_transactions,
    load_budgets,
    load_category_budgets,
)
from transactions import get_transaction_month


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

        print()