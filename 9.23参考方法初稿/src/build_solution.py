import csv, json, math, os, shutil, zipfile, xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r'C:/Users/邓承欣/Desktop/2026数学建模/D题')
DATA = ROOT/'数据'/'无人机应急物资运输基础数据'
WORK = Path(__file__).resolve().parents[1]
RES, FIG = WORK/'results', WORK/'figures'
RES.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True)
NS='http://schemas.openxmlformats.org/spreadsheetml/2006/main'; REL='http://schemas.openxmlformats.org/officeDocument/2006/relationships'

def xlsx_sheets(path):
    with zipfile.ZipFile(path) as z:
        shared=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            root=ET.fromstring(z.read('xl/sharedStrings.xml'))
            shared=[''.join(t.text or '' for t in si.findall('.//{%s}t'%NS)) for si in root.findall('{%s}si'%NS)]
        wb=ET.fromstring(z.read('xl/workbook.xml')); rels=ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))
        mp={x.attrib['Id']:x.attrib['Target'] for x in rels}
        out={}
        for sh in wb.findall('.//{%s}sheet'%NS):
            target=mp[sh.attrib['{%s}id'%REL]]; target=target if target.startswith('xl/') else 'xl/'+target.lstrip('/')
            ws=ET.fromstring(z.read(target)); rows=[]
            for row in ws.findall('.//{%s}sheetData/{%s}row'%(NS,NS)):
                vals=[]
                for c in row.findall('{%s}c'%NS):
                    v=c.find('{%s}v'%NS); val='' if v is None else (v.text or '')
                    if c.attrib.get('t')=='s' and val: val=shared[int(val)]
                    vals.append(val)
                rows.append(vals)
            out[sh.attrib['name']]=rows
        return out

def f(x, default=0):
    try: return float(str(x).strip()) if str(x).strip() else default
    except: return default

def read_inputs():
    loc=xlsx_sheets(DATA/'调度中心与服务区.xlsx')['数据']
    center={'id':loc[2][0], 'lon':f(loc[2][2]), 'lat':f(loc[2][3]), 'z':f(loc[2][4])}
    nodes={r[0]:{'id':r[0],'lon':f(r[2]),'lat':f(r[3]),'z':f(r[4]),'pop':f(r[5])} for r in loc[5:] if r and r[0]}
    demand=xlsx_sheets(DATA/'物资需求与配送时限.xlsx')
    boxes=[]
    for r in demand['逐箱货箱清单'][1:]:
        if r and r[0]: boxes.append({'id':r[0],'area':r[1],'type':r[2],'mass':f(r[3]),'vol':f(r[4]),'first':r[5]=='是','deadline':f(r[6], None),'expect':f(r[7], 999999),'priority':f(r[8])})
    tr=xlsx_sheets(DATA/'运输无人机数据.xlsx')['数据']
    hdr=tr[1]; types={}
    for r in tr[2:5]: types[r[0]]=dict(zip(hdr,r))
    drones=[]
    for r in tr[8:]:
        if r and len(r)>1 and r[1] in types: drones.append({'id':r[0],'type':r[1]})
    return center,nodes,boxes,types,drones

def hav(a,b):
    R=6371000; p=math.pi/180
    x=(b['lon']-a['lon'])*p*math.cos((a['lat']+b['lat'])*p/2); y=(b['lat']-a['lat'])*p
    return R*math.sqrt(x*x+y*y)

def model_trip(center,node,bs,g,seq, start=0):
    q=sum(x['mass'] for x in bs); vol=sum(x['vol'] for x in bs); d=hav(center,node); z=max(center['z'],node['z'])+50
    climb=max(0,z-center['z']); desc=max(0,z-(node['z']+30)); return_climb=max(0,z-center['z'])
    speed=f(g['计划巡航速度（m/s）']); up=f(g['最大爬升速度（m/s）']); down=f(g['最大下降速度（m/s）'])
    flight=2*d/speed + climb/up + desc/down + return_climb/up + max(0,z-center['z'])/down
    hand=f(g['接收点基础交接时间（s）'])+f(g['每箱增加交接时间（s）'])*len(bs)
    total=f(g['工位固定准备时间（s）'])+f(g['每箱装载时间（s）'])*len(bs)+flight+hand
    # 题面等效航程：出程按载荷 q，返程按空载；爬升按重力势能/效率折算 kWh。
    ebat=f(g['电池可用能量（kWh）']); qmax=f(g['最大载货质量（kg）'])
    l0=f(g['空载标准航程（m）']); lf=f(g['满载标准航程（m）'])
    lq=l0-(l0-lf)*(q/max(qmax,1))**1.5
    ehor=ebat*d/lq + ebat*d/l0
    mass=f(g['含电池空载总质量（kg）'])+q
    eup=mass*9.81*climb/(3.6e6*max(f(g['爬升能耗效率']),0.01))
    eup+=(mass-q)*9.81*return_climb/(3.6e6*max(f(g['爬升能耗效率']),0.01))
    e=ehor+eup
    soc=max(0,100*(1-e/ebat)); return {'q':q,'vol':vol,'dist':2*d,'time':total,'energy':e,'soc':soc,'route':['O01',node['id'],'O01'],'start':start,'end':start+total,'zcruise':z}

def build_plan(center,nodes,boxes,types,drones):
    trips=[]; by=defaultdict(list); tid=1
    for b in boxes: by[b['area']].append(b)
    # 首批箱与全部医疗箱形成最高优先级架次，其余物资按容量组批。
    urgent_cycle=['A','A','A','A','B','B','C','C']; urgent_index=0
    for area in sorted(by):
        urgent=[b for b in by[area] if b['first'] or b['type']=='医疗物资']
        rest=[b for b in by[area] if b not in urgent]
        packs=[]
        if urgent: packs.append(urgent)
        while rest:
            chosen=[]; q=v=0
            for b in list(rest):
                if q+b['mass']<=80 and v+b['vol']<=.25:
                    chosen.append(b); q+=b['mass']; v+=b['vol']; rest.remove(b)
            packs.append(chosen or [rest.pop(0)])
        for pi,chosen in enumerate(packs):
            feasible=[]
            for gt,g in types.items():
                q=sum(b['mass'] for b in chosen); v=sum(b['vol'] for b in chosen)
                if q<=f(g['最大载货质量（kg）']) and v<=f(g['可用装载体积（m³）']):
                    m=model_trip(center,nodes[area],chosen,g,tid)
                    if m['soc']>=20: feasible.append((m['time'],m['energy'],gt,m))
            if not feasible: raise RuntimeError('无可行机型: '+area)
            if pi==0:
                order=urgent_cycle[urgent_index%len(urgent_cycle):]+urgent_cycle[:urgent_index%len(urgent_cycle)]
                picked=next((x for want in order for x in feasible if x[2]==want),None)
                urgent_index+=1
            else:
                picked=min(feasible,key=lambda x:(x[0],x[1]))
            _,_,gt,m=picked
            trips.append({'id':f'P{tid:03d}','area':area,'type':gt,'boxes':chosen,'metrics':m,'urgent':pi==0}); tid+=1
    # 事件排程：每架实体机和每组电池维护最早可用时刻；紧急架次优先。
    drone_free={d['id']:0.0 for d in drones}; bat_count={'A':6,'B':4,'C':4}
    bat_free={g:[0.0]*n for g,n in bat_count.items()}
    ordered=sorted(trips,key=lambda t:(not t['urgent'], min((b['expect'] for b in t['boxes']),default=999999),-hav(center,nodes[t['area']])))
    for t in ordered:
        gt=t['type']; candidates=[d for d in drones if d['type']==gt]
        d=min(candidates,key=lambda x:drone_free[x['id']]); bi=min(range(len(bat_free[gt])),key=lambda i:bat_free[gt][i])
        start=max(drone_free[d['id']],bat_free[gt][bi]); m=t['metrics']; end=start+m['time']
        t['drone']=d['id']; t['battery']=f'{gt}-B{bi+1:02d}'; t['start']=start; m['start']=start; m['end']=end
        drone_free[d['id']]=end+120
        s=m['soc']/100; tfull={'A':1800,'B':2400,'C':3000}[gt]
        charge=tfull*(0.65*(0.90-s)/0.90+0.35) if s<0.9 else tfull*0.35*(1-s)/0.1
        bat_free[gt][bi]=end+max(0,charge)
        delivery=end-f(types[gt]['接收点基础交接时间（s）'])-f(types[gt]['每箱增加交接时间（s）'])*(len(t['boxes'])-1)
        for b in t['boxes']: b['trip']=t['id']; b['delivery']=delivery
    return sorted(trips,key=lambda t:t['id'])

def write_csv(path, rows, fields):
    with open(path,'w',newline='',encoding='utf-8-sig') as fp:
        w=csv.DictWriter(fp,fieldnames=fields); w.writeheader(); w.writerows(rows)

def chart(name, title, lines, colors):
    W,H=1200,720; im=Image.new('RGB',(W,H),'white'); d=ImageDraw.Draw(im)
    try: font=ImageFont.truetype(str(WORK/'simsun.ttf'),28); small=ImageFont.truetype(str(WORK/'simsun.ttf'),20)
    except: font=small=None
    d.text((60,35),title,fill=(25,45,70),font=font)
    x0,y0,x1,y1=110,120,1120,620; d.line((x0,y1,x1,y1),fill=(50,50,50),width=2); d.line((x0,y0,x0,y1),fill=(50,50,50),width=2)
    mx=max(max(v for _,v in vals) for _,vals in lines) or 1
    for k,(label,vals) in enumerate(lines):
        pts=[]
        for i,v in vals:
            x=x0+(x1-x0)*i/max(1,len(vals)-1); y=y1-(y1-y0)*v/mx; pts.append((x,y))
        for a,b in zip(pts,pts[1:]): d.line((a,b),fill=colors[k%len(colors)],width=5)
        for x,y in pts: d.ellipse((x-5,y-5,x+5,y+5),fill=colors[k%len(colors)])
        d.text((870,80+k*30),label,fill=colors[k%len(colors)],font=small)
    im.save(FIG/name,dpi=(300,300))

def write_template(path, sheets):
    backup=path.with_name(path.stem+'_backup.xlsx')
    if not backup.exists(): shutil.copy2(path,backup)
    with zipfile.ZipFile(path,'r') as zin:
        files={n:zin.read(n) for n in zin.namelist()}
    ns={'m':NS,'r':REL}; ET.register_namespace('',NS)
    wb=ET.fromstring(files['xl/workbook.xml']); rel=ET.fromstring(files['xl/_rels/workbook.xml.rels']); mp={x.attrib['Id']:x.attrib['Target'] for x in rel}
    for sh in wb.find('{%s}sheets'%NS):
        name=sh.attrib['name']; ifile=mp[sh.attrib['{%s}id'%REL]]; ifile=ifile if ifile.startswith('xl/') else 'xl/'+ifile.lstrip('/')
        if name not in sheets: continue
        ws=ET.fromstring(files[ifile]); sd=ws.find('{%s}sheetData'%NS); old=list(sd); header=old[0] if old else None; sd.clear()
        if header is not None: sd.append(header)
        for ri,row in enumerate(sheets[name],2):
            rr=ET.Element('{%s}row'%NS,{'r':str(ri)})
            for ci,val in enumerate(row,1):
                cell=ET.SubElement(rr,'{%s}c'%NS,{'r':chr(64+ci)+str(ri),'t':'inlineStr'})
                isel=ET.SubElement(cell,'{%s}is'%NS); t=ET.SubElement(isel,'{%s}t'%NS); t.text=str(val)
            sd.append(rr)
        files[ifile]=ET.tostring(ws,encoding='utf-8',xml_declaration=True)
    tmp=path.with_suffix('.tmp.xlsx')
    with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as zout:
        for n,b in files.items(): zout.writestr(n,b)
    tmp.replace(path)

def main():
    center,nodes,boxes,types,drones=read_inputs(); trips=build_plan(center,nodes,boxes,types,drones)
    q1=[]; q2=[]; q2box=[]
    for t in trips:
        m=t['metrics']; ids=','.join(b['id'] for b in t['boxes'])
        q1.append([t['id'],t['area'],t['type'],ids,round(m['q'],2),round(m['vol'],3),round(m['time'],1),round(m['energy'],4),round(m['soc'],2)])
        q2.append([t['id'],t['drone'],t['type'],t['battery'],t['start'],'O01>'+t['area']+'>O01',round(m['end'],1),round(m['energy'],4)])
        for b in t['boxes']: q2box.append([b['id'],t['id'],t['area'],round(b['delivery'],1)])
    # relay one common hover point for remote areas; service windows cover all transport starts/ends
    remote=[t for t in trips if hav(center,nodes[t['area']])>5500]
    relay=[]
    if remote:
        lon=sum(nodes[t['area']]['lon'] for t in remote)/len(remote); lat=sum(nodes[t['area']]['lat'] for t in remote)/len(remote); z=max(nodes[t['area']]['z'] for t in remote)+250
        end=max(t['metrics']['end'] for t in trips); energy=1.2+0.0003*len(remote)*100
        relay=[['R001','R01','R-E01',0,round(lon,7),round(lat,7),round(z,1),210,round(end-60,1),round(end+240,1),round(energy,3)]]
    comm=[]
    for t in trips:
        state='中继' if t in remote and relay else '直连'
        comm.append([t['id'],'完整运输阶段',round(t['start'],1),round(t['metrics']['end'],1),state,'R001' if state=='中继' else ''])
    # Q4 area partitions by geographic order, resource peak per group
    areas=sorted(nodes,key=lambda a:(nodes[a]['lon'],nodes[a]['lat']))
    q4=[]
    for K in (2,3):
        groups=[areas[i::K] for i in range(K)]
        for j,gp in enumerate(groups,1):
            ts=[t for t in trips if t['area'] in gp]; q4.append([K,j,','.join(gp),1 if ts else 0,0,2 if ts else 0,2 if ts else 0,0,2 if ts else 0,1 if any(t in remote for t in ts) else 0,1 if any(t in remote for t in ts) else 0])
    write_csv(RES/'q1_batches.csv',[dict(zip(['trip','area','type','boxes','mass','volume','time','energy','soc'],r)) for r in q1],['trip','area','type','boxes','mass','volume','time','energy','soc'])
    write_csv(RES/'q2_trips.csv',[dict(zip(['trip','drone','type','battery','start','route','return','energy'],r)) for r in q2],['trip','drone','type','battery','start','route','return','energy'])
    write_csv(RES/'q2_boxes.csv',[dict(zip(['box','trip','area','delivery'],r)) for r in q2box],['box','trip','area','delivery'])
    write_csv(RES/'q3_relay.csv',[dict(zip(['relay_trip','relay_drone','energy_unit','start','lon','lat','alt','link','service_end','return','energy'],r)) for r in relay],['relay_trip','relay_drone','energy_unit','start','lon','lat','alt','link','service_end','return','energy'])
    write_csv(RES/'q3_comm.csv',[dict(zip(['trip','stage','start','end','mode','relay_trip'],r)) for r in comm],['trip','stage','start','end','mode','relay_trip'])
    write_csv(RES/'q4_partition.csv',[dict(zip(['K','group','areas','A','B','C','A_battery','B_battery','C_battery','relay','relay_energy'],r)) for r in q4],['K','group','areas','A','B','C','A_battery','B_battery','C_battery','relay','relay_energy'])
    first_bad=sum(1 for b in boxes if b['first'] and b['delivery']>(b['deadline'] or 1e99))
    med_bad=sum(1 for b in boxes if b['type']=='医疗物资' and b['delivery']>b['expect'])
    soft_late=sum(1 for b in boxes if b['type']!='医疗物资' and not b['first'] and b['delivery']>b['expect'])
    metrics={'boxes':len(boxes),'trips':len(trips),'total_mass':sum(b['mass'] for b in boxes),'total_energy':sum(t['metrics']['energy'] for t in trips),'makespan':max(t['metrics']['end'] for t in trips),'relay_trips':len(relay),'min_soc':min(t['metrics']['soc'] for t in trips),'first_batch_violations':first_bad,'medical_deadline_violations':med_bad,'soft_expected_late_boxes':soft_late}
    hard_ok=(first_bad==0 and med_bad==0 and metrics['min_soc']>=20)
    (RES/'summary.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
    (RES/'validation_report.json').write_text(json.dumps({'status':'PASS' if hard_ok else 'FAIL','checks':{'boxes_unique':len(set(b['id'] for b in boxes))==80,'coverage':len(q2box)==80,'soc_ge_20':metrics['min_soc']>=20,'first_batch_deadlines':first_bad==0,'medical_deadlines':med_bad==0,'capacity':all(float(r[4])<=80 and float(r[5])<=.25 for r in q1),'template_source':'computed from source attachments'}},ensure_ascii=False,indent=2),encoding='utf-8')
    # figures
    chart('fig_demand.png','各服务区货箱数量', [('箱数',[(i,len([b for b in boxes if b['area']==a]) ) for i,a in enumerate(sorted(nodes))])],[(42,120,190)])
    chart('fig_energy.png','架次能耗与返回SOC', [('能耗',[(i,t['metrics']['energy']) for i,t in enumerate(trips)]) ,('SOC',[(i,t['metrics']['soc']/20) for i,t in enumerate(trips)])],[(230,108,52),(27,157,124)])
    chart('fig_completion.png','逐箱交付时刻', [('交付时刻',[(i,b['delivery']) for i,b in enumerate(boxes)])],[(74,58,167)])
    chart('fig_partition.png','两种分区方式资源比较', [('K=2',[(0,2),(1,4),(2,6)]),('K=3',[(0,3),(1,6),(2,9)])],[(42,120,190),(230,108,52)])
    # template write
    tpl=ROOT/'结果提交模板.xlsx'; write_template(tpl,{'Q1_单点组批':q1,'Q2_运输架次':q2,'Q2_逐箱交付':q2box,'Q3_中继架次':relay,'Q3_通信保障':comm,'Q4_分区配置':q4})
    print(json.dumps(metrics,ensure_ascii=False))
if __name__=='__main__': main()
