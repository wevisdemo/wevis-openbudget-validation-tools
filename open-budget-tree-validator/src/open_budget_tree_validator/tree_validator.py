from typing import List, Dict, Any
import pandas as pd
import numpy as np

def validate_amount_in_chunk(chunk_df: pd.DataFrame) -> pd.DataFrame:
    """_summary_
    Valdiate amount in a given chunk of the budget tree recursively.
    """
    # Check _depth to break recursive loop
    if len(chunk_df['_depth'].unique()) == 1:
        return chunk_df
    
    # Get first row as header of chunk
    first_row = chunk_df.head(1)
    
    # Get depth of the first row
    current_depth = first_row['_depth'].values[0]
    current_amount = first_row['amount'].values[0]
    
    # Split next depth into chunks
    chunk_ids = (chunk_df['_depth'] == current_depth + 1).cumsum()
    if len(set(chunk_ids)) > 1:
        # Validate each chunk
        validated_chunks = pd.concat(
            [
                validate_amount_in_chunk(_chunk)
                for _id, _chunk in chunk_df.groupby(chunk_ids) if _id > 0
            ],
            ignore_index=True
        )
    else:
        return chunk_df
    
    # Get amount from next depth
    children_sum = validated_chunks[
        validated_chunks['_depth'] == current_depth + 1
    ]['amount'].sum()
    
    if children_sum != current_amount:
        # Construct error message
        error_message = f"ยอดรวมรายการย่อยใต้รายการนี้ ({children_sum:,})"
        error_message += f"ไม่ตรงกับงบของรายการนี้ ({current_amount:,}). "
        if children_sum > current_amount:
            error_message += f"มีมากกว่าอยู่ {children_sum-current_amount:,}"
        else:
            error_message += f"มีน้อยกว่าอยู่ {current_amount-children_sum:,}"
        first_row.loc[:, ['error_message']] = first_row['error_message'].apply(
            lambda old_message: " ".join([old_message, error_message])
        )
    
    return pd.concat(
        [
            first_row,
            validated_chunks
        ],
        ignore_index=True
    )
    
def validate_budget_hierarchy(df: pd.DataFrame) -> pd.DataFrame:
    """_summary_
    Valdiate budget_type in budget tree hierarchy and add error message.
    """
    
    # Split data into `BUDGETARY_UNIT` chunks
    chunk_ids = (df['budget_type'] == 'BUDGETARY_UNIT').cumsum()
    processed_chunks = []
    for _id, chunk in df.groupby(chunk_ids):
        if _id == 0: # skip MINISTRY row
            processed_chunks.append(chunk)
            continue
        
        # Check `BUDGET_PLAN` after `BUDGETARY_UNIT`
        mask = (chunk['budget_type'] == 'BUDGETARY_UNIT') & (chunk['budget_type'].shift(-1) != 'BUDGET_PLAN')
        chunk.loc[mask, ['error_message']] = chunk.loc[mask, ['error_message']].apply(
            lambda old_err_mesg: old_err_mesg + 'ไม่เจอ "แผนงาน" ใต้ "หน่วยรับงบ"' 
        )
        
        # Check `OUTPUT` or `PROJECT` after `BUDGET_PLAN`
        mask = (chunk['budget_type'] == 'BUDGET_PLAN') & \
            ((chunk['budget_type'].shift(-1) != 'OUTPUT') & (chunk['budget_type'].shift(-1) != 'PROJECT')) & \
            ~(chunk['_text'].str.contains(r"^7\.1", regex=True)) # skip 7.1 since it not caintain any OUTPUT nor PROJECT
        chunk.loc[mask, ['error_message']] = chunk.loc[mask, ['error_message']].apply(
            lambda old_err_mesg: old_err_mesg + 'ไม่เจอ "โครงการ" หรือ "ผลผลิต" ใต้ "แผนงาน"'
        )
        
        # Check `BUDGET_DETAIL` after `PROJECT` or `OUTPUT``
        mask = ((chunk['budget_type'] == 'OUTPUT') | (chunk['budget_type'] == 'PROJECT')) & \
            (chunk['budget_type'].shift(-1) != 'BUDGET_DETAIL')
        chunk.loc[mask, ['error_message']] = chunk.loc[mask, ['error_message']].apply(
            lambda old_err_mesg: old_err_mesg + 'ไม่เจอ "รายละเอียดงบประมาณ" ใต้ โครงการหรือผลผลิต'
        )

        processed_chunks.append(chunk)

    return pd.concat(
        processed_chunks, ignore_index=True
    )
    
def validate_and_add_error_message(
    df: pd.DataFrame
) -> pd.DataFrame:
    """_summary_
    Validate and add error message in budget tree.
    """
    budget_tree_df = df.copy()
    
    # Validate Amount
    validated_amount_df = validate_amount_in_chunk(budget_tree_df)
    
    # Validate Hierarchy
    validated_hierarchy_df = validate_budget_hierarchy(validated_amount_df)
    
    return validated_hierarchy_df