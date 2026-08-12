import pandas as pd
from open_budget_tree_validator import BudgetTree

def main():
    # Mock data
    mock_df = pd.read_csv("data/mock_tree_invalid.csv")
    budget_tree = BudgetTree(mock_df)
    
    validated_tree = budget_tree.get_validate_tree()
    validated_tree.to_csv('output/validated.csv', index=False)
    
if __name__ == "__main__":
    main()