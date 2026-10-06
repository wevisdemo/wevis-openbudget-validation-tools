from typing import List
import re
import pandas as pd
from .tree_validator import validate_and_add_error_message
from .tree_auto_corrector import correct_budget_tree
from .utilities import clean_budget_tree, add_depth_and_text, get_closest_match, clean_item_name
from .skeleton_generator import generate_skeleton_from_df, SkeletonBudget
from .final_df_builder import build_final_budget_df

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
        
        # Setup skeleton list
        self.closet: List[SkeletonBudget] = []
        
        # Auto correct budgetary unit names
        self.auto_correct_budgetary_unit_names()
            
    def auto_correct_budgetary_unit_names(self) -> None:
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
        self.budget_tree = budgetary_unit_df
        
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
        Generate a skeleton tree from the budget bureau df and update budget tree
        """
        if self.budget_bureau_df is None:
            return self.budget_tree
        
        self.auto_correct_budgetary_unit_names()
        budget_tree = self.budget_tree
        
        skeletons = generate_skeleton_from_df(self.budget_bureau_df)
        
        # Fill in any missing plan with skeleton
        # Split data into chunks of budgetary unit
        chunk_ids = (budget_tree['budget_type'] == 'BUDGETARY_UNIT').cumsum()
        processed_chunks = []
        for _unit_id, unit_chunk in budget_tree.groupby(chunk_ids):
            if _unit_id == 0: # skip MINISTRY row
                processed_chunks.append(unit_chunk)
                continue
            
            budget_unit_name = unit_chunk.head(1)['_text'].values[0]
            # Split data into chunk of budget_plan
            plan_chunk_ids = (unit_chunk['budget_type'] == 'BUDGET_PLAN').cumsum()
            budgetary_unit_chunks: List[pd.DataFrame] = []
            for _plan_id, plan_chunk in unit_chunk.groupby(plan_chunk_ids):
                budgetary_unit_chunks.append(plan_chunk)
                if _plan_id == 0: # skip BUDGETARY UNIT row
                    continue
                plan_name = plan_chunk.head(1)['_text'].values[0]
                # Check for 7.1 to skip
                if re.search(r"^7\.1", plan_name):
                    continue
                
                # Clean plan name
                plan_name = re.sub(r"7\.\d+\s?", "", plan_name).strip()

                plan_skeletons = [
                    sk for sk in skeletons \
                        if sk.budgetary_unit == budget_unit_name\
                            and sk.budget_plan == plan_name
                ]
                output_names = plan_chunk[plan_chunk['budget_type'].isin(['OUTPUT', 'PROJECT'])]['_text'].values
                
                # Skeleton of missing output/project
                missing_outputs = [
                    sk for sk in plan_skeletons if sk.get_output_text() not in output_names
                ]
                # Add skeleton to closet
                self.closet.extend(missing_outputs)
                
                budgetary_unit_chunks.extend([
                    sk.get_skeleton_tree() for sk in missing_outputs
                ])
            processed_chunks.append(pd.concat(
                budgetary_unit_chunks,
                ignore_index=True
            ))
            
        self.budget_tree = pd.concat(
            processed_chunks,
            ignore_index=True
        )
        return self.budget_tree
    
    def build_final_df(self, budget_year: int):
        
        # Build initial final df
        final_df = build_final_budget_df(self.budget_tree)
        
        # Add budget year for every empty fiscal years
        final_df.loc[:, 'FISCAL_YEAR'] = final_df['FISCAL_YEAR'].fillna(budget_year).astype(int)
        
        # Convert year to AD
        final_df.loc[:, 'FISCAL_YEAR'] = final_df['FISCAL_YEAR'].apply(
            lambda y: y - 543
        )
        
        # Clean names
        # BUDGET_PLAN
        final_df.loc[:, 'BUDGET_PLAN'] = final_df['BUDGET_PLAN'].apply(
            lambda text: clean_item_name(text) if text else ""
        )
        
        # OUTPUT & PROJECT
        final_df.loc[:, 'OUTPUT'] = final_df['OUTPUT'].apply(
            lambda text: clean_item_name(text) if text else ""
        )
        final_df.loc[:, 'PROJECT'] = final_df['PROJECT'].apply(
            lambda text: clean_item_name(text) if text else ""
        )
        
        # CATEGORY_LV1 - CATEGORY_LV7
        for i in range(1, 7+1):
            col = f"CATEGORY_LV{i}"
            final_df.loc[:, col] = final_df[col].apply(
                lambda text: clean_item_name(text) if text else ""
            )
        
        # ITEM_DESCRIPTION
        final_df.loc[:, 'ITEM_DESCRIPTION'] = final_df['ITEM_DESCRIPTION'].apply(
            lambda text: clean_item_name(text) if text else ""
        )
        
        return final_df