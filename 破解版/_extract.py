# -*- coding: utf-8 -*-
import os, docx
base = os.path.join('C:', os.sep, 'Users', '24404', 'Desktop')
target = None
for d in os.listdir(base):
    if '第二十三届' in d and '(2)' in d:
        p = os.path.join(base, d)
        for root, dirs, files in os.walk(p):
            for f in files:
                if f.endswith('.docx') and '洪涝' in f:
                    target = os.path.join(root, f)
print("FOUND:", target)
d = docx.Document(target)
out = []
for para in d.paragraphs:
    t = para.text.strip()
    if t:
        out.append(t)
for i, tb in enumerate(d.tables):
    out.append(f"\n[表格{i+1}]")
    for row in tb.rows:
        cells = [c.text.strip() for c in row.cells]
        out.append(' | '.join(cells))
txt = '\n'.join(out)
open('problem_text.txt', 'w', encoding='utf-8').write(txt)
print("chars:", len(txt))
