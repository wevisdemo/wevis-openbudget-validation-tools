import pandas as pd
from open_budget_tree_validator import BudgetTree

def main():
    # Mock data
    mock_df = pd.read_csv("data/mock_tree_invalid.csv")
    
    # Mock Budget Bureau data
    budget_bureau_df = pd.read_csv("data/mock_budget_bureau.csv")
    
    budget_tree = BudgetTree(mock_df, budget_bureau_df=budget_bureau_df)
    
    validated_tree = budget_tree.get_validate_tree()
    validated_tree.to_csv('output/validated.csv', index=False)
    
    # Mock generate skeleton
    budget_tree.generate_skeleton()
    skeleton_df = budget_tree.get_budget_tree()
    skeleton_df.to_csv('output/skeleton.csv', index=False)
    
if __name__ == "__main__":
    main()