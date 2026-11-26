import json,sys,glob,os,shutil
# usage: page.py <tool-result file> <name>   -> saves as <name>.json, prints summary and next uri
src,name=sys.argv[1],sys.argv[2]
raw=open(src,encoding='utf-8').read()
d=json.loads(raw)
shutil.copy(src,f'{name}.json')
pg=d['page']; ch=d['data']['children']
def cons(e,acc):
    for c in e.get('children',[]):
        if c.get('xmlElementName')=='constraint': acc.append(c)
        else: cons(c,acc)
n=0;ne=0
for e in ch:
    a=[];cons(e,a); n+=len(a); ne+=sum(1 for c in a if c.get('attributes',{}).get('expression'))
print(name,'types',len(ch),'constraints',n,'with expression',ne,'| total',pg.get('total'),'complete',pg.get('complete'))
print('NEXT',pg.get('nextUri',''))
