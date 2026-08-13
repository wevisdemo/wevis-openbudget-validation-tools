import re
import pandas as pd
from .utilities import get_prefix_pattern

def correct_chunk_tree(chunk_df: pd.DataFrame) -> pd.DataFrame:
    
    df = chunk_df.copy()
    
    base_level = df.head(1)['_depth'].values[0]
    levels = [] 
    result = []
    curr = -1
    
    for text in df['_text']:
        pat, val = get_prefix_pattern(str(text))
        
        if pat is None:
            result.append(max(0, curr))
            continue
            
        if curr == -1:
            curr = 0
            levels = [{'pat': pat, 'val': val}]
        elif pat == levels[curr]['pat']:
            if val > levels[curr]['val']:
                levels[curr]['val'] = val
            else:
                curr += 1
                levels = levels[:curr]
                levels.append({'pat': pat, 'val': val})
        else:
            match_idx = next((i for i in range(curr - 1, -1, -1) if levels[i]['pat'] == pat), -1)
            
            if match_idx != -1:
                curr = match_idx
                levels[curr]['val'] = val
                levels = levels[:curr + 1]
            else:
                curr += 1
                levels = levels[:curr]
                levels.append({'pat': pat, 'val': val})
                
        result.append(curr)
    
    # Assign new _drpth
    df['_depth'] = result + base_level
    #  Initialize all columns to empty strings
    for i in range(1, 12):
        df[f'name_{i}'] = ""
    # Place _text into the matching column based on _depth
    for i in range(1, 12):
        mask = df['_depth'].astype(int) == i
        df.loc[mask, f'name_{i}'] = df.loc[mask, '_text']
        
    return df

def correct_budget_tree(df: pd.DataFrame) -> pd.DataFrame:
    """_summary_
    TBA
    """
    
    # Split data into `BUDGETARY_UNIT` chunks
    b_unit_chunk_ids = (df['budget_type'] == 'BUDGETARY_UNIT').cumsum()
    processed_unit_chunks = []
    for _u_id, buget_unit_chunk in df.groupby(b_unit_chunk_ids):
        if _u_id == 0: # skip MINISTRY row
            processed_unit_chunks.append(buget_unit_chunk)
            continue
        
        # Split data into `BUDGET_PLAN` chunks
        b_plan_chunk_ids = (buget_unit_chunk['budget_type'] == 'BUDGET_PLAN').cumsum()
        processed_plan_chunks = []
        for _p_id, budget_plan_chunk in buget_unit_chunk.groupby(b_plan_chunk_ids):
            if _p_id == 0: # skip NUDGETARY_UNIT row
                processed_plan_chunks.append(budget_plan_chunk)
                continue
            
            processed_plan_chunks.append(correct_chunk_tree(budget_plan_chunk))
            
        processed_unit_chunks.append(pd.concat(processed_plan_chunks, ignore_index=True))
        
    return pd.concat(processed_unit_chunks, ignore_index=True)