/**
 * @OnlyCurrentDoc
 */

/**
 * Creates a custom menu in Google Sheets when the document opens.
 */
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('🛠️ Budget Tools')
    .addItem('Validate Budget Tree', 'runBudgetValidation')
    .addToUi();
}

/**
 * Main function to read data, validate, and write back ONLY to Column A.
 */
function runBudgetValidation() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();

  // Skip if Sheet start with `README` or `PROGRESS`
  const sheetName = sheet.getName().toUpperCase()
  if (sheetName.startsWith('README') || sheetName.startsWith('PROGRESS')) {
    return
  }

  const data = sheet.getDataRange().getValues();
  
  // -------------------------------------------------------------
  // ROW LIMIT CHECK: Stop if exceeding 20,000 rows
  // -------------------------------------------------------------
  if (data.length > 20000) {
    SpreadsheetApp.getUi().alert(
      '⚠️ Dataset Too Large', 
      'The dataset exceeds 20,000 rows. Apps Script might time out.\n\nPlease use the more powerful alternative tool prepared for this task.', 
      SpreadsheetApp.getUi().ButtonSet.OK
    );
    return;
  }
  
  if (data.length <= 1) return; // Exit if empty or just headers

  // Extract headers
  const headers = data[0];
  const colIdx = {};
  headers.forEach((h, i) => colIdx[h] = i);

  // Convert 2D array to an Array of Objects
  let allRows = [];
  for (let i = 1; i < data.length; i++) {
    let rowObj = { _orig_idx: i };
    
    // Read all columns from the sheet
    for (let h in colIdx) {
      rowObj[h] = data[i][colIdx[h]];
    }
    
    // 🔥 RESET ERROR MESSAGE: Force it to be blank so old errors are wiped
    rowObj.error_message = ""; 
    
    allRows.push(rowObj);
  }

  // --- Step 0: Add Depth and Text ---
  add_depth_and_text(allRows);

  // --- Step 1: Validate Informations ---
  let validatedRows = validate_informations(allRows);

  // --- Step 2: Validate Amount in chunks recursively ---
  validatedRows = validate_amount_in_chunk(validatedRows);

  // --- Step 3: Validate Budget Hierarchy ---
  validate_budget_hierarchy(validatedRows);

  // --- Step 4: Extract Only Error Messages to Write Back ---
  // We iterate over `allRows` to guarantee original order remains untouched.
  let outputErrors = [];
  allRows.forEach(row => {
    let err = row.error_message || "";
    err = err.replace(/<MISSING>/g, ""); // Clean up any lingering <MISSING> tags
    outputErrors.push([err]); // Must be a 2D array for setValues
  });

  // Write back ONLY to Column A (Column index 1 in GAS), starting at Row 2
  sheet.getRange(2, 1, outputErrors.length, 1).setValues(outputErrors);
  
  const total_error_remain = outputErrors.filter(errm => errm != "").length;
  if (total_error_remain == 0) {
    SpreadsheetApp.getUi().alert('✅ Success', 'Budget Tree Validation is complete!', SpreadsheetApp.getUi().ButtonSet.OK);
  }
  else {
    SpreadsheetApp.getUi().alert('🔍 Error Detected', `Detected ${total_error_remain} error`, SpreadsheetApp.getUi().ButtonSet.OK);
  }
}

/**
 * Dynamically computes _depth and _text from name_1 to name_11 columns.
 */
function add_depth_and_text(rows) {
  rows.forEach(row => {
    row._depth = 999; // Default if missing
    row._text = '<MISSING>';

    // Loop through name_1 to name_11 to find the first populated level
    for (let n = 1; n <= 11; n++) {
      let colKey = 'name_' + n;
      let val = row[colKey];
      
      if (val !== undefined && val !== null && String(val).trim() !== '') {
        row._depth = n;
        row._text = String(val).trim();
        break; // Stop at the first non-empty name_X
      }
    }
  });
  return rows;
}

/**
 * Validates missing informations.
 */
function validate_informations(rows) {
  rows.forEach(row => {
    row.error_message = row.error_message || "";
    if (!row.budget_type) row.error_message += 'ขาดประเภท (`budget_type`). ';
    if (!row.page) row.error_message += 'ขาดหมายเลขหน้า (`page`). ';
    if (!row.document) row.error_message += 'ขาดชื่อเอกสาร (`document`). ';
    if (row._text === '<MISSING>') row.error_message += 'ขาดคอลลัมน์ที่มีชื่อขึ้นต้นด้วย `name_`. ';
    if (Number(row.amount) === -1) row.error_message += '"amount" ไม่ใช่ตัวเลข. ';
  });
  return rows;
}

/**
 * Recursively validates budget amounts by checking parent-child sums.
 */
function validate_amount_in_chunk(rows) {
  if (rows.length === 0) return rows;

  // Check _depth to break recursive loop
  let depths = new Set();
  rows.forEach(r => depths.add(r._depth));
  if (depths.size <= 1) return rows;
  
  let first_row = rows[0];
  let current_depth = Number(first_row._depth);
  let current_amount = Number(first_row.amount) || 0;
  
  // Create cumulative chunks logic (Equivalent to Pandas cumsum)
  let chunk_ids = [];
  let current_id = 0;
  for (let i = 0; i < rows.length; i++) {
    if (Number(rows[i]._depth) === current_depth + 1) {
      current_id++;
    }
    chunk_ids.push(current_id);
  }
  
  let unique_chunk_ids = new Set(chunk_ids);
  let validated_chunks = [];
  
  if (unique_chunk_ids.size > 1) {
    let groups = {};
    for (let i = 0; i < rows.length; i++) {
      let id = chunk_ids[i];
      if (!groups[id]) groups[id] = [];
      groups[id].push(rows[i]);
    }
    
    // Validate each chunk id > 0
    for (let id in groups) {
      if (parseInt(id) > 0) {
        validated_chunks = validated_chunks.concat(validate_amount_in_chunk(groups[id]));
      }
    }
  } else {
    return rows;
  }
  
  // Sum children amounts (Equivalent to clip(lower=0)['amount'].sum())
  let children_sum = 0;
  validated_chunks.forEach(r => {
    if (Number(r._depth) === current_depth + 1) {
      // Ignore the amount if the child row is 'FISCAL_YEAR_BUDGET'
      if (r.budget_type !== 'FISCAL_YEAR_BUDGET') {
        let amt = Number(r.amount) || 0;
        if (amt < 0) amt = 0; // clip(lower=0)
        children_sum += amt;
      }
    }
  });
  
  // Floating point safety for JS math
  children_sum = Math.round(children_sum * 100) / 100;
  
  // Validate parent against the sum as usual
  if (children_sum !== current_amount) {
    let formatNum = (num) => num.toLocaleString('en-US');
    let err = `ยอดรวมรายการย่อยใต้รายการนี้ (${formatNum(children_sum)})ไม่ตรงกับงบของรายการนี้ (${formatNum(current_amount)}) `;
    
    if (children_sum > current_amount) {
      err += `มีมากกว่าอยู่ ${formatNum(children_sum - current_amount)}. `;
    } else {
      err += `มีน้อยกว่าอยู่ ${formatNum(current_amount - children_sum)}. `;
    }
    
    first_row.error_message = (first_row.error_message ? first_row.error_message + " " : "") + err;
  }
  
  // Return group 0 combined with validated_chunks
  let group0 = [];
  for(let i = 0; i < rows.length; i++) {
    if (chunk_ids[i] === 0) group0.push(rows[i]);
  }
  return group0.concat(validated_chunks);
}

/**
 * Validates the hierarchy structure of the budget types.
 */
function validate_budget_hierarchy(rows) {
  let chunk_ids = [];
  let current_id = 0;
  
  // Group by BUDGETARY_UNIT
  for (let i = 0; i < rows.length; i++) {
    if (rows[i].budget_type === 'BUDGETARY_UNIT') {
      current_id++;
    }
    chunk_ids.push(current_id);
  }
  
  let groups = {};
  for (let i = 0; i < rows.length; i++) {
    let id = chunk_ids[i];
    if (!groups[id]) groups[id] = [];
    groups[id].push(rows[i]);
  }
  
  let processed_chunks = [];
  
  for (let idStr in groups) {
    let id = parseInt(idStr);
    let chunk = groups[id];
    
    if (id === 0) { // Skip MINISTRY rows block
      processed_chunks = processed_chunks.concat(chunk);
      continue;
    }
    
    let budgetary_unit_depth = Number(chunk[0]._depth);
    let budgetary_plan_depth = budgetary_unit_depth + 1;
    
    let plan_indexes = [];
    for (let i = 0; i < chunk.length; i++) {
      if (chunk[i].budget_type === 'BUDGET_PLAN') {
        plan_indexes.push(chunk[i]._orig_idx);
      }
    }
    let min_index = plan_indexes.length > 1 ? plan_indexes[1] : 1000000;
    
    for (let i = 0; i < chunk.length; i++) {
      let row = chunk[i];
      row.error_message = row.error_message || "";
      
      let next_type = (i + 1 < chunk.length) ? chunk[i + 1].budget_type : null;
      let depth = Number(row._depth);
      
      // Rule 1: BUDGET_PLAN after BUDGETARY_UNIT
      if (row.budget_type === 'BUDGETARY_UNIT' && next_type !== 'BUDGET_PLAN') {
        row.error_message += 'ไม่เจอ "แผนงาน" ใต้ "หน่วยรับงบ". ';
      }
      
      // Rule 2: OUTPUT or PROJECT after BUDGET_PLAN
      let is7_1 = row._text && String(row._text).match(/^7\.1/);
      if (row.budget_type === 'BUDGET_PLAN' && 
          next_type !== 'OUTPUT' && next_type !== 'PROJECT' && 
          !is7_1) {
        row.error_message += 'ไม่เจอ "โครงการ" หรือ "ผลผลิต" ใต้ "แผนงาน". ';
      }
      
      // Rule 3: BUDGET_DETAIL after PROJECT or OUTPUT
      if ((row.budget_type === 'OUTPUT' || row.budget_type === 'PROJECT') && 
          next_type !== 'BUDGET_DETAIL') {
        row.error_message += 'ไม่เจอ "รายละเอียดงบประมาณ" ใต้ โครงการหรือผลผลิต. ';
      }
      
      // Rule 4: Hierarchy Level - BUDGET_PLAN
      if (depth === budgetary_unit_depth + 1 && row.budget_type !== 'BUDGET_PLAN') {
        row.error_message += 'category level ควรเป็น BUDGET_PLAN. ';
      }
      
      // Rule 5: Hierarchy Level - OUTPUT and PROJECT
      if (row._orig_idx > min_index && 
          depth === budgetary_plan_depth + 1 && 
          row.budget_type !== 'OUTPUT' && row.budget_type !== 'PROJECT') {
        row.error_message += 'category level ควรเป็น OUTPUT หรือ PROJECT. ';
      }
    }
    
    processed_chunks = processed_chunks.concat(chunk);
  }
  
  return processed_chunks;
}