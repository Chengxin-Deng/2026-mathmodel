# -*- coding: utf-8 -*-
import os
for user in ['24404','Administrator']:
    dt = os.path.join('C:',os.sep,'Users',user,'Desktop')
    print(user,'Desktop exists:', os.path.exists(dt))
    if os.path.exists(dt):
        try:
            for d in os.listdir(dt):
                if '研究生' in d or '中文' in d or '洪涝' in d:
                    print('  ->',repr(d))
        except Exception as e:
            print('  err',e)
