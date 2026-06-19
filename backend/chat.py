import os
import re
import json
import uuid
from ai import (
    analyze_text,
    generate_insights_response,
    generate_advice_response,
    answer_monthly_question_response,
    detect_anomalies_response,
    recategorize_response,
)
from storage import (
    load_saved_transactions,
    save_all_transactions,
    save_transactions,
    load_category_budgets,
    save_category_budgets,
)
from validators import (
    ALLOWED_CATEGORIES,
    ALLOWED_TYPES,
    validate_transactions,
    user_mentioned_money,
    has_description,
    is_valid_date,
)
from json_utils import parse_llm_json
from budgets import (
    set_category_budget,
)
from transactions import (
    get_transaction_month,
    review_transactions,
    show_transactions,
    view_transaction,
    delete_transaction,
    edit_transaction,
    add_transaction_ids,
)
from finance_ai import (
    generate_monthly_insights,
    generate_monthly_advice,
    ask_monthly_question,
    detect_monthly_anomalies,
    recategorize_month,
    ask_monthly_question
)
from summaries import show_monthly_summary
from recurring import (
    add_recurring_expense,
    show_recurring_expenses,
    delete_recurring_expense,
)
def ask_for_amount() -> str:
    while True:
        amount = input("How much did you spend? ")

        if amount.lower() in ["exit", "quit"]:
            exit()

        if user_mentioned_money(amount):
            return amount

        print("Please enter a valid amount, for example: 10, 10 euros, or €10")


def show_help():
    print("""
Available commands:

Expense input:
  chocolate 10
  spent 12 euros on Uber
  paid 25 at Continente
  yesterday I spent 9.99 euros on Netflix

Transactions:
  transactions
  transactions MM-YYYY
  view transaction_id
  edit transaction_id field new_value
  delete transaction_id

Budgets:
  category-budget MM-YYYY Category amount

Summaries:
  summary
  summary MM-YYYY

AI features:
  insights MM-YYYY
  advice MM-YYYY
  ask MM-YYYY your question
  anomalies MM-YYYY
  recategorize MM-YYYY

Recurring expenses:
  recurring
  add-recurring name amount category
  delete-recurring recurring_id
          
Note:
  Monthly budget is calculated automatically from monthly income.      

Other:
  help
  exit
""")
    
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

    if user_input.lower() == "recurring":
        show_recurring_expenses()
        continue


    if user_input.lower().startswith("add-recurring "):
        parts = user_input.split()

        if len(parts) < 4:
            print("Use: add-recurring name amount category")
            print("Example: add-recurring Netflix 14 Subscriptions")
            continue

        name = " ".join(parts[1:-2])
        amount = float(parts[-2])
        category = parts[-1]

        add_recurring_expense(name, amount, category)
        continue


    if user_input.lower().startswith("delete-recurring "):
        parts = user_input.split()

        if len(parts) != 2:
            print("Use: delete-recurring recurring_id")
            continue

        recurring_id = parts[1]

        delete_recurring_expense(recurring_id)
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