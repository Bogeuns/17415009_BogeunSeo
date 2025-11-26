import pandas as pd
import os
import xlsxwriter
import sys

try:
    file_input = input("Enter the file number (e.g., 0.5): ").strip()
except KeyboardInterrupt:
    sys.exit()

csv_filename = f"{file_input}.csv"

if not os.path.exists(csv_filename):
    print(f"Error: File '{csv_filename}' not found.")
    sys.exit()

try:
    file_value = float(file_input)
except ValueError:
    file_value = 0.5

df = pd.read_csv(csv_filename)

if 'Points_1' not in df.columns or 'Pressure' not in df.columns:
    print("Error: 'Points_1' or 'Pressure' columns are missing in the CSV file.")
    sys.exit()

P_at = 101325
r = 0.143 + file_value
omega = 261.7993878
v = r * omega
q = 0.5 * 1.225 * (v**2)

section_percent = int(round(file_value * 100))
chart_title_text = f"Section {section_percent}%"

df['P_minus_Pat'] = df['Pressure'] - P_at
df['Cp'] = df['P_minus_Pat'] / q

sheet3_data = df[['Points_1', 'Cp']].copy()
sheet3_data = sheet3_data.sort_values(by='Points_1', ascending=False).reset_index(drop=True)

tags = []
n_rows = len(sheet3_data)

for i in range(n_rows):
    if i == 0:
        val = 1
    elif i == 1:
        val = 1
    elif i == 2:
        val = 2
    elif i == n_rows - 1:
        val = 2
    else:
        if i % 2 != 0:
            val = 1
        else:
            val = 2
    tags.append(val)

sheet3_data['SortKey'] = tags
sheet3_data = sheet3_data.sort_values(by=['SortKey', 'Points_1'], ascending=[False, False])

output_filename = f"{file_input}.xlsx"
writer = pd.ExcelWriter(output_filename, engine='xlsxwriter')
workbook = writer.book

sheet1 = workbook.add_worksheet('Sheet1')

sheet1.write('A1', 'Points_1')
sheet1.write('B1', 'Pressure')
sheet1.write('C1', 'P-P_at')
sheet1.write('E1', 'Parameters')
sheet1.write('F1', 'Values')
sheet1.write('G1', 'Cp')

params = [('r', r), ('omega', omega), ('v', v), ('q', q)]

for i, row in df.iterrows():
    sheet1.write(i+1, 0, row['Points_1'])
    sheet1.write(i+1, 1, row['Pressure'])
    sheet1.write(i+1, 2, row['P_minus_Pat'])
    sheet1.write(i+1, 6, row['Cp'])
    
    if i < len(params):
        sheet1.write(i+1, 4, params[i][0])
        sheet1.write(i+1, 5, params[i][1])

sheet2 = workbook.add_worksheet('Sheet2')
sheet2.write(0, 0, 'Points_1')
sheet2.write(0, 1, 'Pressure')
for i, row in df.iterrows():
    sheet2.write(i+1, 0, row['Points_1'])
    sheet2.write(i+1, 1, row['Pressure'])

sheet3 = workbook.add_worksheet('Sheet3')
sheet3.write('A1', 'SortKey')
sheet3.write('B1', 'Points_1')
sheet3.write('C1', 'Cp')

data_rows = sheet3_data.to_dict('records')
current_excel_row = 1
inserted_row_index = -1
previous_tag = None

for i, row_data in enumerate(data_rows):
    current_tag = row_data['SortKey']
    
    if previous_tag == 2 and current_tag == 1:
        inserted_row_index = current_excel_row
        current_excel_row += 1
    
    sheet3.write(current_excel_row, 0, current_tag)
    sheet3.write(current_excel_row, 1, row_data['Points_1'])
    sheet3.write(current_excel_row, 2, row_data['Cp'])
    
    previous_tag = current_tag
    current_excel_row += 1

last_data_row = current_excel_row

range_str = f"B2:B{last_data_row}"
sheet3.write_formula('E2', f'=MAX({range_str})')
sheet3.write_formula('E3', f'=MIN({range_str})')
sheet3.write_formula('E4', '=E2-E3')

sheet3.write('G1', 'Points_1')
sheet3.write('H1', 'Cp')

for r_idx in range(1, last_data_row):
    if r_idx == inserted_row_index:
        continue
        
    excel_row = r_idx + 1
    g_formula = f'=(B{excel_row}-$E$3)/$E$4'
    h_formula = f'=C{excel_row}'
    
    sheet3.write_formula(r_idx, 6, g_formula)
    sheet3.write_formula(r_idx, 7, h_formula)

chart = workbook.add_chart({'type': 'scatter', 'subtype': 'straight'})
chart.add_series({
    'name':       'SU2',
    'categories': ['Sheet3', 1, 6, last_data_row - 1, 6],
    'values':     ['Sheet3', 1, 7, last_data_row - 1, 7],
    'line':       {'color': 'black', 'width': 2},
})

chart.set_title ({'name': chart_title_text})
chart.set_x_axis({
    'name': 'X/C',
    'label_position': 'low',
})
chart.set_y_axis({
    'name': 'Cp',
})

sheet3.insert_chart('J2', chart)

writer.close()
print("Done.")