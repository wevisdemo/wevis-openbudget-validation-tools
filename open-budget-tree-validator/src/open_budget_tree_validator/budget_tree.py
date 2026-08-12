import re
import pandas as pd
from .tree_validator import validate_and_add_error_message
from .utilities import add_depth_and_text

class BudgetTree():
    def __init__(self, budget_tree_df: pd.DataFrame):
        
        # Add _text and _depth
        self.budget_tree = add_depth_and_text(budget_tree_df.fillna(''))
        
        # Clean & Normalize amount to be int
        self.budget_tree.loc[:, ['amount']] = self.budget_tree['amount'].apply(
            lambda amount: re.sub(r"\,|\_", "", str(amount)).strip()
        )
        self.budget_tree['amount'] = self.budget_tree['amount'].astype(int)
        
    
    def get_budget_tree(self) -> pd.DataFrame:
        """_summary_
        Get a full budget tree as pandas dataframe
        """
        return self.budget_tree
    
    def get_validate_tree(self) -> pd.DataFrame:
        """_summary_
        Validate tree and add error explanation to `error_message` column
        """
        validated_tree_df = validate_and_add_error_message(self.budget_tree)
        
        cleaned_tree_df = validated_tree_df.drop(
            columns=['_text', '_depth'],
            axis=1
        )
        return cleaned_tree_df
        