import pandas as pd
from open_budget_tree_validator import BudgetTree

def main():
    # Mock data
    mock_df = pd.read_csv("data/mock_tree_invalid.csv")
    budget_tree = BudgetTree(mock_df)
    
    validated_tree = budget_tree.get_validate_tree()
    validated_tree.to_csv('output/validated.csv', index=False)
    
    # Mock auto correct hierarchy
    mock_df = pd.read_csv("data/mock_tree_hierarchy.csv")
    budget_tree = BudgetTree(mock_df)
    budget_tree.auto_correct_tree()
    
    corrected_tree = budget_tree.get_budget_tree()
    corrected_tree.to_csv('output/corrected.csv', index=False)
    
if __name__ == "__main__":
    main()