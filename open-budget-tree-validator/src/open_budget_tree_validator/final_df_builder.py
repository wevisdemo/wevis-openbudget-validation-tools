from typing import List, Dict, Any
import re
import pandas as pd
import numpy as np

def process_budget_items(
    items_df: pd.DataFrame,
    ministry: str|None=None,
    budgetary_unit: str|None=None,
    budget_plan: str|None=None,
    output:str|None=None,
    project:str|None=None,
    categories_lv: list=[]
) -> pd.DataFrame:
        
    category = categories_lv + ["" for _ in range(7 - len(categories_lv))]
    
    data = []
    group_ids = (items_df['budget_type'] != 'FISCAL_YEAR_BUDGET').cumsum()
    for _, _chunk in items_df.groupby(group_ids):
        first_row = _chunk.head(1)
        item_name = first_row['_text'].values[0]
        item_amount = first_row['amount'].values[0]
        if len(_chunk.index) == 1: # not a fiscal year
            data.append({
                'REF_DOC': items_df['document'].values[0],
                'REF_PAGE_NO': items_df['page'].values[0],
                'MINISTRY': ministry,
                'BUDGETARY_UNIT': budgetary_unit,
                'BUDGET_PLAN': budget_plan,
                'CROSS_FUNC?': budget_plan and bool(re.search(r"แผนงานบูรณาการ", budget_plan)),
                'OUTPUT': output,
                'PROJECT': project,
                'CATEGORY_LV1': category[0],
                'CATEGORY_LV2': category[1],
                'CATEGORY_LV3': category[2],
                'CATEGORY_LV4': category[3],
                'CATEGORY_LV5': category[4],
                'CATEGORY_LV6': category[5],
                'CATEGORY_LV7': category[6],
                'ITEM_DESCRIPTION': item_name,
                'AMOUNT': item_amount,
                'FISCAL_YEAR': None,
                'OBLIGED?': False,
                '_document': items_df['document'].values[0],
                '_page': items_df['page'].values[0],
            })
            continue
            
        # Is fiscal year
        for _, row in _chunk.iloc[1:].iterrows():
            
            fiscal_text = row['_text']
            fiscal_amount = row['amount']
            
            matched_numbers = [
                int(n) for n in re.findall(r"25\d{2}", fiscal_text)
            ]
            splited_amount = fiscal_amount / ((max(matched_numbers) + 1) - min(matched_numbers))
            for year in range(min(matched_numbers), max(matched_numbers) + 1):
                data.append({
                    'REF_DOC': items_df['document'].values[0],
                    'REF_PAGE_NO': items_df['page'].values[0],
                    'MINISTRY': ministry,
                    'BUDGETARY_UNIT': budgetary_unit,
                    'BUDGET_PLAN': budget_plan,
                    'CROSS_FUNC?': budget_plan and bool(re.search(r"แผนงานบูรณาการ", budget_plan)),
                    'OUTPUT': output,
                    'PROJECT': project,
                    'CATEGORY_LV1': category[0],
                    'CATEGORY_LV2': category[1],
                    'CATEGORY_LV3': category[2],
                    'CATEGORY_LV4': category[3],
                    'CATEGORY_LV5': category[4],
                    'CATEGORY_LV6': category[5],
                    'CATEGORY_LV7': category[6],
                    'ITEM_DESCRIPTION': item_name,
                    'AMOUNT': splited_amount,
                    'FISCAL_YEAR': year,
                    'OBLIGED?': True,
                    '_document': items_df['document'].values[0],
                    '_page': items_df['page'].values[0],
                })
        
    return pd.DataFrame(data)

def build_final_budget_df(
    chunk_df: pd.DataFrame,
    ministry: str | None = None,
    budgetary_unit: str | None = None,
    budget_plan: str | None = None,
    output: str | None = None,
    project: str | None = None,
    categories_lv: list | None = None
) -> pd.DataFrame:
    """_summary_
    Build final budget df from budget tree recursively.
    """
    if categories_lv is None:
        categories_lv = []

    if chunk_df.empty:
        return pd.DataFrame()

    # --- BASE CASE: Leaf Node (Item + Fiscal Years) ---
    # If the chunk contains exactly ONE non-fiscal-year row, it is a single item.
    # It should be processed directly along with its fiscal years, regardless 
    # of whether the fiscal years are at the same depth or a different depth!
    non_fy_mask = chunk_df['budget_type'] != 'FISCAL_YEAR_BUDGET'
    if non_fy_mask.sum() == 1:
        return process_budget_items(
            chunk_df,
            ministry=ministry,
            budgetary_unit=budgetary_unit,
            budget_plan=budget_plan,
            output=output,
            project=project,
            categories_lv=categories_lv,
        )

    # Handle edge case where a chunk somehow only contains orphaned fiscal years
    if non_fy_mask.sum() == 0:
        return process_budget_items(
            chunk_df, ministry=ministry, budgetary_unit=budgetary_unit,
            budget_plan=budget_plan, output=output, project=project,
            categories_lv=categories_lv
        )

    # --- Sibling Splitting ---
    # Find the minimum depth among the non-fiscal-year rows.
    # This depth represents the root(s) of the current chunk.
    min_depth = chunk_df.loc[non_fy_mask, '_depth'].min()
    
    # Identify all root nodes in this chunk
    is_root = (chunk_df['_depth'] == min_depth) & non_fy_mask
    
    # If there are multiple siblings at this root level, split them into separate subtrees.
    if is_root.sum() > 1:
        chunk_ids = is_root.cumsum()
        return pd.concat(
            [
                build_final_budget_df(
                    _chunk,
                    ministry=ministry,
                    budgetary_unit=budgetary_unit,
                    budget_plan=budget_plan,
                    output=output,
                    project=project,
                    categories_lv=categories_lv,
                )
                for i, _chunk in chunk_df.groupby(chunk_ids)
                if i > 0 # Skip any orphaned rows before the first root
            ],
            ignore_index=True
        )

    # --- Process Single Subtree ---
    # At this point, we are guaranteed to have exactly ONE root node (parent).
    first_row = chunk_df[is_root].head(1)
    root_idx = first_row.index[0]
    
    current_type = first_row['budget_type'].values[0]
    current_text = first_row['_text'].values[0]
        
    # --- Context Update ---
    match current_type:
        case 'MINISTRY': ministry = current_text
        case 'BUDGETARY_UNIT': budgetary_unit = current_text
        case 'BUDGET_PLAN': budget_plan = current_text
        case 'OUTPUT': output = current_text
        case 'PROJECT': project = current_text
        case _: categories_lv = categories_lv + [current_text]

    # --- Recursive Chunking ---
    # The children are all rows strictly AFTER the root node.
    root_iloc = chunk_df.index.get_loc(root_idx)
    children_df = chunk_df.iloc[root_iloc + 1:] # type: ignore
    
    if children_df.empty:
        return pd.DataFrame()

    return build_final_budget_df(
        children_df,
        ministry=ministry,
        budgetary_unit=budgetary_unit,
        budget_plan=budget_plan,
        output=output,
        project=project,
        categories_lv=categories_lv,
    )