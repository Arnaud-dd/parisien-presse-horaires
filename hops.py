# Tracés des sauts entre gares (pour la carte), d'après les tracés des lignes
import json,math,os,sys
OUT=os.environ.get('OUT','.').rstrip('/')+'/'
N=json.load(open(OUT+'tt.json')); S=N['S']; L=N['L']; sh=json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'shapes_all.json')))
KX,KY=73,111
xy=lambda p:(p[0]*KX,p[1]*KY)
def proj(poly,P):
  px,py=xy(P); best=None; s=0
  for i in range(len(poly)-1):
    ax,ay=xy(poly[i]); bx,by=xy(poly[i+1]); dx,dy=bx-ax,by-ay; L2=dx*dx+dy*dy; Ln=math.sqrt(L2)
    t=0 if L2==0 else max(0,min(1,((px-ax)*dx+(py-ay)*dy)/L2))
    d=math.hypot(px-ax-t*dx,py-ay-t*dy)
    if best is None or d<best[0]: best=(d,s+t*Ln,i)
    s+=Ln
  return best
def dp(points,tol):
  if len(points)<3: return points
  (ax,ay),(bx,by)=xy(points[0]),xy(points[-1]); dx,dy=bx-ax,by-ay; Ln=math.hypot(dx,dy) or 1e-9
  md=-1;mi=0
  for i in range(1,len(points)-1):
    px,py=xy(points[i]); d=abs(dy*(px-ax)-dx*(py-ay))/Ln
    if d>md: md,mi=d,i
  if md>tol: return dp(points[:mi+1],tol)[:-1]+dp(points[mi:],tol)
  return [points[0],points[-1]]
dk=lambda p,Q:math.hypot((p[0]-Q[0])*KX,(p[1]-Q[1])*KY)
hops=set()
for P in N['P']:
  li,sts=P[0],P[1]
  if L[li][3]==3: continue
  for a,b in zip(sts,sts[1:]): hops.add((li,min(a,b),max(a,b)))
out={}
for li,a,b in sorted(hops):
  A=[S[a][2],S[a][1]]; B=[S[b][2],S[b][1]]; straight=dk(A,B); best=None
  for poly in sh.get(L[li][0],[]):
    pa=proj(poly,A); pb=proj(poly,B)
    if pa[0]>0.35 or pb[0]>0.35: continue
    ln=abs(pb[1]-pa[1])
    if ln>2.2*straight+0.3 or ln<0.6*straight: continue
    sc=pa[0]+pb[0]+0.05*ln
    if best is None or sc<best[0]:
      mid=poly[pa[2]+1:pb[2]+1] if pa[1]<=pb[1] else poly[pb[2]+1:pa[2]+1][::-1]
      ra=min(max(0.08,3*pa[0]),0.4*straight); rb=min(max(0.08,3*pb[0]),0.4*straight)
      mid=[p for p in mid if dk(p,A)>ra and dk(p,B)>rb]
      best=(sc,[A]+mid+[B])
  if not best: continue
  s=dp(best[1],0.008)[1:-1]
  if s: out[f'{li}|{a}|{b}']=' '.join(f'{round((p[0]-A[0])*1e5)},{round((p[1]-A[1])*1e5)}' for p in s)
print('sauts ferrés',len(hops),'avec tracé',len(out),file=sys.stderr)
json.dump(out,open(OUT+'hopshapes.json','w'),separators=(',',':'))
