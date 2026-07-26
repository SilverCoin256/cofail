import json,urllib.request,urllib.parse,pandas as pd,io,re,hashlib
API="https://huggingface.co/api/datasets/"; RES="https://huggingface.co/datasets/{}/resolve/main/{}"
def get(u): return urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'r'}),timeout=60).read()
def load(m):
    meta=json.loads(get(API+m))
    f=sorted([s['rfilename'] for s in meta.get('siblings',[]) if 'arc:challenge' in s['rfilename']])[-1]
    return pd.read_parquet(io.BytesIO(get(RES.format(m,urllib.parse.quote(f)))))
def key(s):
    q=re.sub(r'\s+',' ',str(s)).strip().lower()
    return hashlib.md5(q.encode()).hexdigest()[:16]
A=load("open-llm-leaderboard-old/details_Corianas__Quokka_2.7b")   # ID-scheme model
B=load("open-llm-leaderboard-old/details_Corianas__Quokka_590m")   # text-scheme model
A['k']=A['query'].map(key)      # same content, different column
B['k']=B['example'].map(key)
ka,kb=set(A.k),set(B.k)
print("A keys=%d  B keys=%d  INTERSECTION=%d  overlap=%.1f%%"%(len(ka),len(kb),len(ka&kb),100*len(ka&kb)/max(len(ka),len(kb))))
inter=sorted(ka&kb)
if len(inter)>100:
    da=A.drop_duplicates('k').set_index('k').loc[inter,'acc'].astype(int)
    db=B.drop_duplicates('k').set_index('k').loc[inter,'acc'].astype(int)
    cf=float(((da==0)&(db==0)).mean()); pa,pb=da.mean(),db.mean()
    print("\nHARMONIZED MATRIX: items=%d"%len(inter))
    print("  acc(A)=%.3f  acc(B)=%.3f"%(pa,pb))
    print("  RAW co-failure   = %.4f"%cf)
    print("  INDEP prediction = %.4f  (product of failure rates)"%((1-pa)*(1-pb)))
    print("  --> raw excess over independence = %+.4f"%(cf-(1-pa)*(1-pb)))
    print("\n(This is the exact quantity the project says is CONFOUNDED by item difficulty;")
    print(" the margin-preserving null replaces the naive independence baseline.)")
