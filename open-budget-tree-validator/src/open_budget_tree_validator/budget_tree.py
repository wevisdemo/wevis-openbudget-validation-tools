import re
import pandas as pd
from .tree_validator import validate_and_add_error_message
from .tree_auto_corrector import correct_budget_tree
from .utilities import clean_budget_tree, add_depth_and_text, get_closest_match
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
        
        # Auto correct budgetary unit names
        self.auto_correct_budgetary_unit_names()
            
    def auto_correct_budgetary_unit_names(self):
        if self.budget_bureau_df is None:
            return
        
        # Clean budgetary unit name
        budgetary_unit_names = list(self.budget_bureau_df['agc_name'].unique())
        budgetary_unit_df = self.budget_tree.copy()
        mask = budgetary_unit_df['budget_type'] == 'BUDGETARY_UNIT'
        # Get matches
        matches = budgetary_unit_df.loc[mask, '_text'].apply(
            lambda name: get_closest_match(name, budgetary_unit_names)
        )
        # Assign the result to name_2 and _text columns
        budgetary_unit_df.loc[mask, 'name_2'] = matches
        budgetary_unit_df.loc[mask, '_text'] = matches
        
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
        
        budget_tree = self.get_budget_tree()
        
        skeletons = generate_skeleton_from_df(self.budget_bureau_df)
        skeleton_df = pd.concat(
            [sk.get_skeleton_tree() for sk in skeletons],
            ignore_index=True
        )
        # Normalize skeleton columns
        skeleton_df[[
            col for col in budget_tree.columns if col not in skeleton_df.columns
        ]] = ''
        skeleton_df = skeleton_df[self.get_budget_tree().columns]
        
        # TODO
        # Fill in any missing plan with skeleton
        
        return skeleton_df