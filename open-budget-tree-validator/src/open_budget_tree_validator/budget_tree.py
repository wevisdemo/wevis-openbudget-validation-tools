import re
import pandas as pd
from .tree_validator import validate_and_add_error_message
from .tree_auto_corrector import correct_budget_tree
from .utilities import clean_budget_tree, add_depth_and_text
from .skeleton_generator import generate_skeleton_from_df

class BudgetTree():
    def __init__(
        self, 
        budget_tree_df: pd.DataFrame,
        budget_bureau_df: pd.DataFrame|None=None
    ):
        
        # Clean budget tree
        self.budget_tree = clean_budget_tree(budget_tree_df)
        
        # Add _depth and _text
        self.budget_tree = add_depth_and_text(self.budget_tree)
        
        # Budget Bureau df
        self.budget_bureau_df = budget_bureau_df
        
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
        
    def auto_correct_tree(self) -> None:
        self.budget_tree = correct_budget_tree(self.budget_tree)
        
    def generate_skeleton(self) -> pd.DataFrame:
        """_summary_
        Generate a skeleton tree from the budget bureau df
        """
        if self.budget_bureau_df is None:
            return self.budget_tree
        
        skeleton_df = generate_skeleton_from_df(self.budget_bureau_df)
        # Normalize skeleton columns
        skeleton_df[[
            col for col in self.get_budget_tree().columns if col not in skeleton_df.columns
        ]] = ''
        skeleton_df = skeleton_df[self.get_budget_tree().columns]
        
        return skeleton_df