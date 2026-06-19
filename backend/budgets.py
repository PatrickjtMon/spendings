from validators import ALLOWED_CATEGORIES
from storage import (
    load_category_budgets,
    save_category_budgets,
)



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