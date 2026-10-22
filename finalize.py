# Assemble les fichiers téléchargés par l'appli : horaires.json (horaires + tracés) et quais.json (pour le temps réel)
import csv,json,re,os,sys
G=os.environ.get('GTFS').rstrip('/')+'/'; OUT=os.environ.get('OUT','.').rstrip('/')+'/'
N=json.load(open(OUT+'tt.json')); N['H']=json.load(open(OUT+'hopshapes.json'))
json.dump(N,open(OUT+'horaires.json','w'),ensure_ascii=False,separators=(',',':'))
z=set()
for s in N['S']: z.update(str(s[3]).split(','))
Q={}
for r in csv.DictReader(open(G+'stops.txt',encoding='utf-8-sig')):
    if r['location_type'] not in ('0',''): continue
    m=re.search(r'(\d+)$',r['stop_id']); p=re.search(r'(\d+)$',r['parent_station'] or '')
    if m and p and p.group(1) in z: Q[m.group(1)]=int(p.group(1))
for x in z:
    if x and x not in Q: Q[x]=int(x)
json.dump(Q,open(OUT+'quais.json','w'),separators=(',',':'))
print('horaires.json',os.path.getsize(OUT+'horaires.json'),'quais.json',os.path.getsize(OUT+'quais.json'),'à partir du',N['D0'],file=sys.stderr)
