from typing import Tuple, List
import re
import pandas as pd
from .constants import PREFIX_PATTERNS
import Levenshtein

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

def get_prefix_pattern(text: str) -> Tuple[str|None, int|None]:
  # Get text and extract prefix pattern and order of the prefix
  text = text.strip()
  for pattern, order in PREFIX_PATTERNS:
    match = re.match(pattern, text)
    if match:
      if order is None:
        return pattern, 0
      return pattern, int(match.group(order))
  return None, None

def get_closest_match(
    text: str, 
    match_pool: List[str],
    threshold: float=0.92
) -> str:
    
    # for word in match_pool:
    #     dist = Levenshtein.distance(text, word)
    #     ratio = Levenshtein.ratio(text, word)
    #     print(f"Target: {text} | Compare: {word} | Distance: {dist} | Ratio: {ratio:.2f}")

    # Find the best match from the list based on highest ratio
    best_match = max(match_pool, key=lambda w: Levenshtein.ratio(text, w))
    if Levenshtein.ratio(text, best_match) >= threshold:
        return best_match
    return text
    