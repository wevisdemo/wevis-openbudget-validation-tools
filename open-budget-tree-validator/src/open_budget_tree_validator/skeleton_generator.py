from typing import List, Tuple
import pandas as pd

BUDGET_DETAIL_PRIORITY = {
    'งบบุคลากร': 0,
    'งบดำเนินงาน': 1,
    'งบลงทุน': 2,
    'งบเงินอุดหนุน': 3,
    'งบรายจ่ายอื่น': 4,
}

class SkeletonBudget():
    def __init__(
        self, 
        budgetary_unit: str,
        budget_plan: str,
        output: str,
        output_amount: int
    ):
        self.budgetary_unit = budgetary_unit
        self.budget_plan = budget_plan
        self.output = output
        self.output_amount = output_amount
        self.budget_details: List[Tuple[str, int]] = []
        
        # Budget type
        if output.startswith('โครงการ'):
            self.budget_type = 'PROJECT'
        else:
            self.budget_type = 'OUTPUT'
        
    def add_budget_detail(
        self, 
        budget_category_name: str,
        amount: int,
    ) -> None:
        self.budget_details.append((budget_category_name, amount))
        
    def get_output_text(self) -> str:
        output_text = "โครงการ : " + self.output if self.budget_type == 'PROJECT' else "ผลผลิต : " + self.output
        return output_text
        
    def get_skeleton_tree(self) -> pd.DataFrame:
        """_summary_
        Get a skeleton budget tree as pandas dataframe start from output level
        """
        output_rows = [[self.budget_type, self.get_output_text(), '', '', self.output_amount]]
        for _idx, (_detail, _amount) in enumerate(self.budget_details):
            output_rows.append(['BUDGET_DETAIL', '', _detail, '', _amount])
            output_rows.append(['BUDGET_DETAIL', '', '', f'{_idx}.1 xxxxx', 0])
        
        return pd.DataFrame(output_rows, columns=['budget_type', 'name_4', 'name_5', 'name_6', 'amount'])

def generate_skeleton_from_df(
    df: pd.DataFrame,
    budgetary_unit_column_name: str='agc_name',
    budget_plan_column_name: str='plan_name',
    output_column_name: str='output_name',
    budget_detail_column_name: str='objc_5',
    amount_column_name: str='p_total_bud'
) -> List[SkeletonBudget]:
    """_summary_
    Generate budget tree skeleton based on dataframe of Budget Bureau 13 fields sheet.
    The dataframe parsed to this function should be filtered to contain data from only one ministry.
    """
    
    skeleton_list = []
    # Group by agc_name
    for agc, agc_df in df.groupby(budgetary_unit_column_name, sort=False):
        # Group by plan_name
        for plan, plan_df in agc_df.groupby(budget_plan_column_name, sort=False):
            # Group by output
            for output, output_df in plan_df.groupby(output_column_name, sort=False):
                
                output_amount = output_df[amount_column_name].sum()
                # Instantiate new skeleton object
                output_skeleton = SkeletonBudget(str(agc), str(plan), str(output), output_amount)
                
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
                    
                    # Add budget detail to skeleton
                    output_skeleton.add_budget_detail(objc_text, objc_amount)

                skeleton_list.append(output_skeleton)
    
    return skeleton_list