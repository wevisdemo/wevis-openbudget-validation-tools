import pandas as pd

BUDGET_DETAIL_PRIORITY = {
    'งบบุคลากร': 0,
    'งบดำเนินงาน': 1,
    'งบลงทุน': 2,
    'งบเงินอุดหนุน': 3,
    'งบรายจ่ายอื่น': 4,
}

def generate_skeleton_from_df(
    df: pd.DataFrame,
    budgetary_unit_column_name: str='agc_name',
    budget_plan_column_name: str='plan_name',
    output_column_name: str='output_name',
    budget_detail_column_name: str='objc_5',
    amount_column_name: str='p_total_bud'
) -> pd.DataFrame:
    """_summary_
    Generate budget tree skeleton based on dataframe of Budget Bureau 13 fields sheet.
    The dataframe parsed to this function should be filtered to contain data from only one ministry.
    """
    
    result_rows = []
    # Group by agc_name
    for agc, agc_df in df.groupby(budgetary_unit_column_name, sort=False):
        # Get sum amount
        agc_amount = agc_df[amount_column_name].sum()
        # Add Level 1 (BUDGETARY_UNIT)
        result_rows.append(['BUDGETARY_UNIT'] + [agc, '', '', '', ''] + [agc_amount])
        
        # Group by plan_name
        for plan, plan_df in agc_df.groupby(budget_plan_column_name, sort=False):
            # Get sum amount
            plan_amount = plan_df[amount_column_name].sum()
            # Get prefix
            _plan_prefix_num = '7.1' if plan == 'แผนงานบุคากรภาครัฐ' else '7.x'
            plan_text = f"{_plan_prefix_num} {plan}"
            # Add Level 2 (BUDGET_PLAN)
            result_rows.append(['BUDGET_PLAN'] + ['', plan_text, '', '', ''] + [plan_amount])
            
            for output, output_df in plan_df.groupby(output_column_name, sort=False):
                # Get sum amount
                output_amount = output_df[amount_column_name].sum()
                # Add prefix โครงการ/ผลผลิต
                _budget_type = 'PROJECT' if str(output).startswith('โครงการ') else 'OUTPUT'
                output_text = 'โครงการ : ' + str(output) if _budget_type == 'PROJECT' else 'ผลผลิต : ' + str(output)
                if _plan_prefix_num != '7.1':
                    # Add Level 3 (OUTPUT/PROJECT)
                    result_rows.append([_budget_type] + ['', '', output_text, '', ''] + [output_amount])
            
                # Iterate through the deepest values
                objc_list = list(output_df[budget_detail_column_name].unique())
                objc_list.sort(key=lambda x: BUDGET_DETAIL_PRIORITY.get(x, 1000))
                for objc in objc_list:
                    objc_df = output_df[output_df[budget_detail_column_name] == objc]
                    # Get sum amount
                    objc_amount = objc_df[amount_column_name].sum()
                    # Get prefix number
                    _prefix_num = objc_list.index(objc) + 1
                    objc_text = f"{_prefix_num}. {objc}"
                    # Add Level 3 (objc_5)
                    result_rows.append(
                        ['BUDGET_DETAIL'] + \
                            (['', '', '', objc_text, ''] if _plan_prefix_num != '7.1' else ['', '', objc_text, '', ''])\
                                + [objc_amount]
                    )
                    
                    # Add Level 4 (Extra row)
                    # Format the string to attach ".1 xxxxx" to the objc_5 value
                    extra_val = f"{_prefix_num}.1 xxxxx"
                    result_rows.append(
                        ['BUDGET_DETAIL'] + \
                            (['','', '', '', extra_val] if _plan_prefix_num != '7.1' else ['','', '', extra_val, ''])\
                                + [0]
                    )

    # Create the new DataFrame
    out_df = pd.DataFrame(
        result_rows, 
        columns=['budget_type', 'name_2', 'name_3', 'name_4', 'name_5', 'name_6', 'amount']
    )
    
    return out_df