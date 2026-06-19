from storage import (
    load_saved_transactions,
    load_category_budgets,
)
from transactions import get_transaction_month
from recurring import get_recurring_status_for_month


def show_monthly_summary(month_filter=None):
    transactions = load_saved_transactions()
    category_budgets = load_category_budgets()

    if not transactions:
        print("No transactions saved yet.")
        return

    monthly_totals = {}

    for transaction in transactions:
        transaction_month = get_transaction_month(transaction["date"])

        if month_filter and transaction_month != month_filter:
            continue

        if transaction_month not in monthly_totals:
            monthly_totals[transaction_month] = {
                "income": 0,
                "expenses": 0,
                "savings": 0,
                "categories": {},
            }

        amount = transaction["amount"]
        category = transaction["category"]
        transaction_type = transaction["type"]

        if amount > 0 and transaction_type == "income":
            monthly_totals[transaction_month]["income"] += amount

        elif amount < 0:
            expense_amount = abs(amount)

            if category == "Savings":
                monthly_totals[transaction_month]["savings"] += expense_amount
            else:
                monthly_totals[transaction_month]["expenses"] += expense_amount

            monthly_totals[transaction_month]["categories"][category] = (
                monthly_totals[transaction_month]["categories"].get(category, 0)
                + expense_amount
            )

    if not monthly_totals:
        print("No transactions found for that month.")
        return

    for month, data in monthly_totals.items():
        monthly_budget = data["income"]
        total_expenses = data["expenses"]
        total_savings = data["savings"]
        total_outflow = total_expenses + total_savings
        remaining = monthly_budget - total_outflow

        if monthly_budget > 0:
            savings_rate = total_savings / monthly_budget
        else:
            savings_rate = 0

        print(f"\nSummary for {month}:")
        print(f"Income / Budget: €{monthly_budget:.2f}")
        print(f"Expenses: €{total_expenses:.2f}")
        print(f"Savings: €{total_savings:.2f}")
        print(f"Total allocated: €{total_outflow:.2f}")
        print(f"Remaining: €{remaining:.2f}")
        print(f"Savings rate: {savings_rate * 100:.1f}%")

        if monthly_budget == 0:
            print("Status: No income recorded for this month.")
        elif remaining < 0:
            print(f"Status: Over income by €{abs(remaining):.2f}")
        else:
            print(f"Status: Within income by €{remaining:.2f}")

        print("\nBy category:")

        month_category_budgets = category_budgets.get(month, {})

        for category, total in data["categories"].items():
            category_budget = month_category_budgets.get(category)

            if category_budget is not None:
                category_remaining = category_budget - total

                if category_remaining < 0:
                    print(
                        f"- {category}: €{total:.2f} / €{category_budget:.2f} "
                        f"(over by €{abs(category_remaining):.2f})"
                    )
                else:
                    print(
                        f"- {category}: €{total:.2f} / €{category_budget:.2f} "
                        f"(remaining €{category_remaining:.2f})"
                    )
            else:
                print(f"- {category}: €{total:.2f} / no category budget")

        month_transactions = [
            transaction
            for transaction in transactions
            if get_transaction_month(transaction["date"]) == month
        ]

        recurring_status = get_recurring_status_for_month(month, month_transactions)

        if recurring_status:
            recurring_total = 0
            paid_recurring_total = 0
            unpaid_recurring_total = 0

            print("\nRecurring expenses:")

            for item in recurring_status:
                amount = abs(item["amount"])
                recurring_total += amount

                if item["status"] == "paid":
                    paid_recurring_total += amount
                else:
                    unpaid_recurring_total += amount

                print(
                    f"- {item['name']}: €{amount:.2f} "
                    f"({item['category']}) - {item['status']}"
                )

            print(f"\nRecurring total: €{recurring_total:.2f}")
            print(f"Paid recurring: €{paid_recurring_total:.2f}")
            print(f"Unpaid recurring: €{unpaid_recurring_total:.2f}")

        print()