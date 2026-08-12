import re
import pandas as pd
from .tree_validator import validate_and_add_error_message
from .utilities import clean_budget_tree, add_depth_and_text

class BudgetTree():
    def __init__(self, budget_tree_df: pd.DataFrame):
        
        # Clean budget tree
        self.budget_tree = clean_budget_tree(budget_tree_df)
        
        # Add _depth and _text
        self.budget_tree = add_depth_and_text(self.budget_tree)
        
    def get_budget_tree(self) -> pd.DataFrame:
        """_summary_
        Get a full budget tree as pandas dataframe
        """
        
        columns_to_drop = [col for col in self.budget_tree.columns if col.startswith("_")]
        
        return self.budget_tree.drop(
            columns=columns_to_drop,
            axis=1
        )
    
    def get_validate_tree(self) -> pd.DataFrame:
        """_summary_
        Validate tree and add error explanation to `error_message` column
        """
        self.budget_tree = validate_and_add_error_message(self.budget_tree)
        
        return self.get_budget_tree()
        