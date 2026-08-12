from typing import List, Dict, Any
import pandas as pd
import numpy as np

def validate_amount_in_chunk(chunk_df: pd.DataFrame) -> pd.DataFrame:
    
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
    nested_amounts = validated_chunks[
        validated_chunks['_depth'] == current_depth + 1
    ]['amount'].sum()
    
    if nested_amounts != current_amount:
        first_row.loc[:, ['error_message']] = f"Amount mismatch: expected {current_amount}, got {nested_amounts}"
    
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
    
    budget_tree_df = df.copy()
    
    # Validate Amount
    validated_amount_df = validate_amount_in_chunk(budget_tree_df)
    
    # Validate Hierarchy
    # TODO: Implement hierarchy validation
    
    return validated_amount_df