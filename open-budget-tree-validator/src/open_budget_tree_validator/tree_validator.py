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
    # Validate each chunk
    validated_chunks = pd.concat(
        [
            validate_amount_in_chunk(_chunk)
            for _id, _chunk in chunk_df.groupby(chunk_ids) if _id > 0
        ],
        ignore_index=True
    )
    
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
    # TODO: Implement hierarchy validation
    
    return validated_amount_df