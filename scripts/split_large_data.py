"""Keep each JSON download below 8 MB for portable static hosting."""
import json,pathlib
p=pathlib.Path(__file__).resolve().parents[1]/'docs/data'
limit=6_500_000
for f in p.glob('c*.json'):
 if '-part-' in f.name or f.stat().st_size<8_000_000:continue
 d=json.loads(f.read_text());parts=[];chunk=[];size=0
 fragments=[]
 for donor in d['donors']:
  donor_size=len(json.dumps(donor,separators=(',',':')).encode())
  if donor_size<=limit:
   fragments.append(donor);continue
  base={k:v for k,v in donor.items() if k!='transactions'};tx=[];tx_size=0
  for row in donor['transactions']:
   row_size=len(json.dumps(row,separators=(',',':')).encode())+1
   if tx and tx_size+row_size>limit:
    fragments.append({**base,'transactions':tx});tx=[];tx_size=0
   tx.append(row);tx_size+=row_size
  if tx:fragments.append({**base,'transactions':tx})
 for donor in fragments:
  ds=len(json.dumps(donor,separators=(',',':')).encode())+1
  if chunk and size+ds>limit:
   name=f'{f.stem}-part-{len(parts)+1}.json';(p/name).write_text(json.dumps(chunk,separators=(',',':')));parts.append(name);chunk=[];size=0
  chunk.append(donor);size+=ds
 if chunk:
  name=f'{f.stem}-part-{len(parts)+1}.json';(p/name).write_text(json.dumps(chunk,separators=(',',':')));parts.append(name)
 d['donors']=[];d['parts']=parts;f.write_text(json.dumps(d,separators=(',',':')));print(f.name,len(parts),'parts')
