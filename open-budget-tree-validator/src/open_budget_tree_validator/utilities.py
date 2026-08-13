import re
import pandas as pd

def clean_budget_tree(df: pd.DataFrame) -> pd.DataFrame:
    cleaned_budget_df = df.fillna('')
    
    # Clean & Normalize amount to be int
    cleaned_budget_df.loc[:, ['amount']] = cleaned_budget_df['amount'].apply(
        lambda amount: re.sub(r"\,|\_", "", str(amount)).strip() if amount else '-1'
    )
    cleaned_budget_df['amount'] = cleaned_budget_df['amount'].astype(int)
    
    # Clean name_X columns
    name_cols = [f'name_{x}' for x in range(1, 12)]
    contain_text_mask = (cleaned_budget_df[name_cols] != '').any(axis=1) # mask
    # Update 'name_2' to `MISSING` if none of columns contain text
    cleaned_budget_df.loc[~contain_text_mask, 'name_2'] = "<MISSING>"
    
    return cleaned_budget_df

def get_text_and_depth(row):
  for i in range(1, 11+1):
    if row[f'name_{i}'] != '':
     return row[f'name_{i}'], i
  return '', None

def add_depth_and_text(budget_tree: pd.DataFrame) -> pd.DataFrame:
    assert all(
        col in budget_tree.columns for col in [
            f"name_{n}" for n in range(1, 11+1)
        ]
    )
    
    budget_tree[['_text', '_depth']] = budget_tree.apply(
        get_text_and_depth,
        axis=1, result_type='expand'
    )
    
    return budget_tree