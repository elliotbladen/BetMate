import openpyxl
wb = openpyxl.load_workbook(r"C:\Users\ElliotBladen\Apps\data\nrl\historical\latest.xlsx", read_only=True, data_only=True)
ws = wb.active
teams = set()
for row in ws.iter_rows(min_row=2, values_only=True):
    if row and row[0]:
        teams.add(str(row[2]))
        teams.add(str(row[3]))
for t in sorted(teams):
    print(t)
wb.close()
