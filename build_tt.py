# Horaires complets (ferré + bus) pour le moteur RAPTOR de l'Itinéraire (Parisien Pressé)
# Usage : GTFS=dossier/du/gtfs OUT=dossier/de/sortie [START=AAAAMMJJ] python3 build_tt.py
# Les horaires réels des 7 jours à partir de START (aujourd'hui par défaut, heure de Paris) :
# travaux, jours fériés et horaires spéciaux annoncés par IDFM sont donc pris en compte.
import csv, json, math, statistics, datetime as dt, sys, os
from collections import defaultdict
from zoneinfo import ZoneInfo
G=os.environ.get('GTFS','/tmp/claude-0/gtfs/GTFS IDFM/').rstrip('/')+'/'
OUT=os.environ.get('OUT','/tmp/claude-0/geo/tt/').rstrip('/')+'/'
rd=lambda f: csv.DictReader(open(G+f,encoding='utf-8-sig'))
KX,KY=73,111
# --- lignes ---
R={}
for r in rd('routes.txt'):
    if r['route_type'] in ('0','1','2','3','6','7') and r['route_short_name']!='TER':
        R[r['route_id']]=dict(n=r['route_short_name'].replace('3B','3bis').replace('7B','7bis'),t=int(r['route_type']),c='#'+(r['route_color'] or '888888'),tc='#'+(r['route_text_color'] or 'FFFFFF'),id=r['route_id'])
# --- jours ---
cal={c['service_id']:c for c in rd('calendar.txt')}
exc=defaultdict(dict)
for c in rd('calendar_dates.txt'): exc[c['date']][c['service_id']]=c['exception_type']
START=os.environ.get('START') or dt.datetime.now(ZoneInfo('Europe/Paris')).strftime('%Y%m%d')
d0=dt.date(int(START[:4]),int(START[4:6]),int(START[6:]))
DATES=[(d0+dt.timedelta(days=i)).strftime('%Y%m%d') for i in range(7)]
print('jours',DATES[0],'→',DATES[-1],file=sys.stderr)
WD=['monday','tuesday','wednesday','thursday','friday','saturday','sunday']
def active(sid,d):
    e=exc[d].get(sid)
    if e: return e=='1'
    c=cal.get(sid)
    if not c: return False
    wd=WD[dt.date(int(d[:4]),int(d[4:6]),int(d[6:])).weekday()]
    return c['start_date']<=d<=c['end_date'] and c[wd]=='1'
T={}
for t in rd('trips.txt'):
    if t['route_id'] in R:
        days=[i for i,d in enumerate(DATES) if active(t['service_id'],d)]
        if days: T[t['trip_id']]=(t['route_id'],days,t.get('wheelchair_accessible','0'))
print('courses',len(T),file=sys.stderr)
stops={s['stop_id']:s for s in rd('stops.txt')}
par=lambda sid: stops[sid]['parent_station'] or sid
ST=defaultdict(list)
def sec(h):
    if not h: return None
    a,b,c=h.split(':'); return int(a)*3600+int(b)*60+int(c)
with open(G+'stop_times.txt',encoding='utf-8-sig') as f:
    r=csv.reader(f); h=next(r); I={k:i for i,k in enumerate(h)}
    for row in r:
        tid=row[I['trip_id']]
        if tid in T: ST[tid].append((int(row[I['stop_sequence']]),row[I['stop_id']],sec(row[I['arrival_time']]),sec(row[I['departure_time']]),row[I['pickup_type']],row[I['drop_off_type']]))
# horaires manquants (arrêts sans heure) : interpolés
for tid,seq in list(ST.items()):
    seq.sort(); a=[x[2] if x[2] is not None else x[3] for x in seq]
    known=[i for i,v in enumerate(a) if v is not None]
    if len(known)<2: del ST[tid]; continue
    for i in range(len(a)):
        if a[i] is None:
            lo=max(k for k in known if k<i) if any(k<i for k in known) else None; hi=min(k for k in known if k>i) if any(k>i for k in known) else None
            a[i]=a[lo] if hi is None else a[hi] if lo is None else a[lo]+(a[hi]-a[lo])*(i-lo)/(hi-lo)
    ST[tid]=[(x[0],x[1],int(a[i]),int(a[i]),x[4],x[5]) for i,x in enumerate(seq)]
print('horaires lus',file=sys.stderr)
# --- arrêts regroupés : zone d'arrêt (parent), puis même nom à moins de 300 m ---
used=defaultdict(set); railArea=set()
for tid,seq in ST.items():
    rt=R[T[tid][0]]['t']
    for x in seq:
        p=par(x[1]); used[p].add(x[1])
        if rt!=3: railArea.add(p)
pos={p:(statistics.mean(float(stops[s]['stop_lat']) for s in v),statistics.mean(float(stops[s]['stop_lon']) for s in v)) for p,v in used.items()}
name=lambda p: stops[p]['stop_name']
order=sorted(used,key=lambda p:(p not in railArea,-len(used[p])))
grid=defaultdict(list); grp={}; reps=[]
for p in order:
    la,lo=pos[p]; gk=(int(la*200),int(lo*140)); hit=None
    for dx in (-1,0,1):
        for dy in (-1,0,1):
            for q in grid[(gk[0]+dx,gk[1]+dy)]:
                if name(q)==name(p) and math.hypot((pos[q][0]-la)*KY,(pos[q][1]-lo)*KX)<0.3: hit=q; break
            if hit: break
        if hit: break
    if hit: grp[p]=hit
    else: grp[p]=p; reps.append(p); grid[gk].append(p)
SI={p:i for i,p in enumerate(reps)}
members=defaultdict(list)
for p,q in grp.items(): members[q].append(p)
S=[]
for p in reps:
    allst=[s for m in members[p] for s in used[m]]
    S.append([name(p),round(statistics.mean(float(stops[s]['stop_lat']) for s in allst),5),round(statistics.mean(float(stops[s]['stop_lon']) for s in allst),5),','.join(sorted(m.replace('IDFM:','') for m in members[p] if m.replace('IDFM:','').isdigit()))])
print('arrêts regroupés',len(S),'dont ferrés',sum(1 for p in reps if p in railArea or any(m in railArea for m in members[p])),file=sys.stderr)
LI={r:i for i,r in enumerate(R)}
L=[[R[r]['n'],R[r]['c'],R[r]['tc'],R[r]['t'],R[r]['id'].replace('IDFM:','')] for r in R]
# --- parcours (motifs) et courses ---
pat={}
for tid,seq in ST.items():
    r,days,twa=T[tid]
    st=[(SI[grp[par(sid)]],a,d,pu,do,stops[sid].get('wheelchair_boarding','0') or '0') for _,sid,a,d,pu,do in sorted(seq)]
    s2=[]
    for x in st:
        if s2 and s2[-1][0]==x[0]: s2[-1]=(x[0],s2[-1][1],x[2],x[3],x[4],max(s2[-1][5],x[5]))
        else: s2.append(x)
    if len(s2)<2: continue
    key=(LI[r],tuple(x[0] for x in s2))
    P=pat.setdefault(key,{'off':[],'trips':[[] for _ in DATES],'nob':None,'wb':[set() for _ in s2],'tw':0})
    t0=s2[0][2]
    P['off'].append([x[1]-t0 for x in s2])
    for d in days: P['trips'][d].append(t0)
    for i,x in enumerate(s2): P['wb'][i].add(x[5])                   # accessibilité des quais (1 oui, 2 non, 0 inconnu)
    if twa!='2': P['tw']=1                                             # au moins une course accessible (ou inconnue)
    if P['nob'] is None: P['nob']=[1 if (x[3]=='1') else 0 for x in s2]   # pas de montée possible
Pout=[]
for (li,sts),v in pat.items():
    off=[round(statistics.median(o[i] for o in v['off'])/60,1) for i in range(len(sts))]
    tr=[sorted(round(t/60,1) for t in v['trips'][d]) for d in range(len(DATES))]
    if not any(tr): continue
    enc=lambda a: [a[0]]+[round(a[i]-a[i-1],1) for i in range(1,len(a))] if a else []
    U=[]; dm=[]
    for x in tr:                                                       # jours identiques : stockés une seule fois
        if not x: dm.append(-1); continue
        if x not in U: U.append(x)
        dm.append(U.index(x))
    wf=''.join('1' if '1' in w else '2' if w=={'2'} else '0' for w in v['wb'])
    Pout.append([li,list(sts),enc(off),[enc(x) for x in U],dm,wf,v['tw']])
print('parcours',len(Pout),'arrêts cumulés',sum(len(p[1]) for p in Pout),'courses',sum(len(x) for p in Pout for x in p[3]),file=sys.stderr)
# --- correspondances officielles (quai à quai), regroupées par arrêt+ligne ---
platRoute=defaultdict(set)
for tid,seq in ST.items():
    for x in seq: platRoute[x[1]].add(LI[T[tid][0]])
X={}
for t in rd('transfers.txt'):
    a,b=t['from_stop_id'],t['to_stop_id']
    if a not in platRoute or b not in platRoute: continue
    sa,sb=SI[grp[par(a)]],SI[grp[par(b)]]; m=int(t['min_transfer_time'] or 0)/60
    for la in platRoute[a]:
        for lb in platRoute[b]:
            if sa==sb and la==lb: continue
            k=(sa,la,sb,lb)
            if k not in X or m<X[k]: X[k]=m
# ferré ↔ ferré : par ligne ; dès qu'un bus est en jeu : par paire d'arrêts (sans détail de ligne)
isbus=lambda li: L[li][3]==3
Xout=[]; XA={}
for (a,la,b,lb),m in X.items():
    if not isbus(la) and not isbus(lb): Xout.append([a,la,b,lb,round(m,1)])
    elif a!=b:
        k=(a,b)
        if k not in XA or m<XA[k]: XA[k]=m
XAout=[[a,b,round(m,1)] for (a,b),m in XA.items()]
print('correspondances ferré',len(Xout),'arrêts',len(XAout),file=sys.stderr)
# --- entrées : position + temps entrée→quai par ligne (pathways) ---
E=defaultdict(lambda: defaultdict(list)); ent2st={}
for p in rd('pathways.txt'):
    a,b,t=p['from_stop_id'],p['to_stop_id'],p['traversal_time']
    if not t: continue
    ent,plat=(a,b) if stops[a]['location_type']=='2' else (b,a)
    if plat not in platRoute: continue
    ent2st[ent]=SI[grp[par(plat)]]
    for li in platRoute[plat]: E[ent][li].append(int(t))
Eout=[]
for ent,d in E.items():
    s=stops[ent]; fl=[]
    for li,v in d.items(): fl+=[li,round(min(v)/60,2)]
    Eout.append([ent2st[ent],round(float(s['stop_lat']),5),round(float(s['stop_lon']),5),fl])
json.dump({'D0':DATES[0],'S':S,'L':L,'P':Pout,'X':Xout,'XA':XAout,'E':Eout},open(OUT+'tt.json','w'),ensure_ascii=False,separators=(',',':'))
print('taille',os.path.getsize(OUT+'tt.json'),file=sys.stderr)
