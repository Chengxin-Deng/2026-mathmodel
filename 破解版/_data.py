# -*- coding: utf-8 -*-
import os, openpyxl, io
base = os.path.join('C:', os.sep, 'Users', '24404', 'PycharmProjects', 'pythonProject1', '2026年研赛D题', '无人机应急物资运输基础数据')
out = io.StringIO()
for f in sorted(os.listdir(base)):
    if not f.endswith('.xlsx'):
        continue
    out.write("\n############ " + f + " ############\n")
    wb = openpyxl.load_workbook(os.path.join(base, f), data_only=True)
    for ws in wb.worksheets:
        out.write(f"--- sheet: {ws.title}  ({ws.max_row}x{ws.max_column}) ---\n")
        for r in ws.iter_rows(values_only=True):
            cells = ['' if c is None else str(c) for c in r]
            if any(cells):
                out.write(' | '.join(cells) + "\n")
open('data_dump.txt', 'w', encoding='utf-8').write(out.getvalue())
print("done", len(out.getvalue()))
