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
            print(item_name)
            print(category)
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
                'OBLIGED?': False
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
                    'OBLIGED?': True
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

    # BASE CASE 1: Deepest level reached
    # If the chunk consists entirely of rows at the SAME depth, 
    # there are no further sub-levels. This perfectly captures 
    # a single item, or an item + its FISCAL_YEAR_BUDGET rows!
    if len(chunk_df['_depth'].unique()) == 1:
        return process_budget_items(
            chunk_df,
            ministry=ministry,
            budgetary_unit=budgetary_unit,
            budget_plan=budget_plan,
            output=output,
            project=project,
            categories_lv=categories_lv,
        )

    # Get first row as header of chunk
    first_row = chunk_df.head(1)
    
    current_type = first_row['budget_type'].values[0]
    current_text = first_row['_text'].values[0]
        
    # --- Context Update ---
    # Update context variables BEFORE processing children
    match current_type:
        case 'MINISTRY':
            ministry = current_text
        case 'BUDGETARY_UNIT':
            budgetary_unit = current_text
        case 'BUDGET_PLAN':
            budget_plan = current_text
        case 'OUTPUT':
            output = current_text
        case 'PROJECT':
            project = current_text
        case _:
            # Create a new list for this branch specifically
            categories_lv = categories_lv + [current_text]

    # --- Recursive Chunking ---
    children_df = chunk_df.iloc[1:]
    
    # BASE CASE 2 (Speed Optimization):
    # If all remaining children are at the same depth, they are leaf nodes.
    # Pass them as a batch to process_budget_items so fiscal years are processed together.
    if len(children_df['_depth'].unique()) == 1:
        return process_budget_items(
            children_df,
            ministry=ministry,
            budgetary_unit=budgetary_unit,
            budget_plan=budget_plan,
            output=output,
            project=project,
            categories_lv=categories_lv,
        )

    # Find the depth of the immediate children (using .min() prevents bugs if depth skips numbers e.g. 6 to 8)
    next_depth = children_df['_depth'].min()
    
    # Split next depth into chunks. Every sibling sub-tree gets its own chunk.
    # FIX: FISCAL_YEAR_BUDGET rows do NOT start a new chunk; they stick to their parent item!
    is_new_chunk = (children_df['_depth'] == next_depth) & (children_df['budget_type'] != 'FISCAL_YEAR_BUDGET')
    chunk_ids = is_new_chunk.cumsum()
    
    # Process each chunk recursively and combine
    process_df = pd.concat(
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
            for _, _chunk in children_df.groupby(chunk_ids)
        ],
        ignore_index=True
    )

    return process_df