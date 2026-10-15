import pandas as pd
from open_budget_tree_validator import BudgetTree

def main():
    
    # Mock auto correct hierarchy
    mock_df = pd.read_csv("data/mock_tree_complete.csv")
    budget_tree = BudgetTree(mock_df, 2570)
    # budget_tree.auto_correct_tree()
    
    final_df = budget_tree.build_final_df(2570)
    final_df.to_csv('output/final_df.csv', index=False)
    
if __name__ == "__main__":
    main()