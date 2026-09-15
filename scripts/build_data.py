"""Build the portable snapshot from extracted records and the reviewed entity registry.
No fuzzy donor matching. All money is stored in integer cents.
"""
import json,re,html,collections,pathlib,hashlib,csv,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
WORK=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else 'work')
def norm(s):return re.sub(r'[^A-Z0-9]+',' ',html.unescape(s).upper().replace("'",'').replace('’','')).strip()
def has(s,a):return (' '+a+' ') in (' '+s+' ')
entities=json.loads((ROOT/'research/entities.json').read_text())
for e in entities:e['_aliases']=[norm(a) for a in e['aliases']]
def match(text):
 s=norm(text);out=[]
 for e in entities:
  if e['id']=='ibew' and re.search(r'\b(LOCAL|LU|L U)\s*\d',s):continue
  if any(has(s,a) for a in e['_aliases']):out.append(e['id'])
 return out
cs=json.load(open(WORK/'mapped.json'));reports=json.load(open(WORK/'selected_reports.json'));tx=collections.defaultdict(list)
for line in open(WORK/'transactions.jsonl'):
 d=json.loads(line);tx[d['filer']].append(d)
report_by=collections.defaultdict(list)
for r in reports:report_by[r['FILERID'].upper()].append(r)
entity_by={e['id']:e for e in entities}; missing=[]; donors_out=[]; matches_out=[]; count=0
for c in cs:
 records=[];reps=[]
 for m in c['filers']:records+=tx[m['filer_id']];reps+=report_by[m['filer_id']]
 groups={}
 for d in records:
  key='|'.join(norm(d[k]) for k in ['donor','city','state'])
  did=hashlib.sha256(key.encode()).hexdigest()[:16]
  if did not in groups:groups[did]={'id':did,'name':html.unescape(d['donor']) or '(blank contributor name)','city':d['city'],'state':d['state'],'transactions':[]}
  direct=match(d['donor']);emp=match(d['employer']); associations=[]
  for eid in direct:associations.append({'entity':eid,'basis':'PAC / organization name' if re.search(r'\b(PAC|COPE|POLITICAL|GOVT|GOVERNMENT|PGG)\b',norm(d['donor'])) else 'Organization name','field':'contributor','value':d['donor']})
  for eid in emp:
   if eid not in direct:associations.append({'entity':eid,'basis':'Reported employer','field':'employer','value':d['employer']})
  d['connections']=associations
  d['lead']=not associations and bool(re.search(r'\b(DATA CENTER|DATA CENTERS|IBEW|CARPENTERS|STEAMFITTERS|PLUMBERS|OPERATING ENGINEERS|LABORERS|SHEET METAL|BUILDING TRADES|FIRSTENERGY|EXELON|PECO|ROB INDALE|ROB INDALE|ROBIND ALE|ROBIND A LE|ROBIND[A-Z]*|NETRALITY|COREWEAVE|POWERHOUSE|DIGITAL REALTY|MCGUIREWOODS|K L GATES|GREENBERG TRAURIG|EQT)\b',norm(d['donor']+' '+d['employer'])))
  groups[did]['transactions'].append(d)
  for a in associations:
   e=entity_by[a['entity']];matches_out.append(dict(candidate_id=c['id'],candidate=c['name'],donor=d['donor'],date=d['date'],amount=d['cents']/100,entity=e['name'],basis=a['basis'],reported_employer=d['employer'],connection=e['claim'],source_url=e['url'],evidence_date=e['evidence_date'],report_id=d['report'],source_record=d['record'],slot=d['slot']))
 for g in groups.values():
  donors_out.append(dict(candidate_id=c['id'],candidate=c['name'],donor=g['name'],city=g['city'],state=g['state'],amount=sum(d['cents'] for d in g['transactions'])/100,transactions=len(g['transactions']),documented_transactions=sum(bool(d['connections']) for d in g['transactions'])))
 c['transaction_count']=len(records);c['donor_count']=len(groups);c['report_count']=len(reps);c['has_committee']=any(m['type']=='2' for m in c['filers']);c['federal_gap']=c['office_code']=='USC'
 c['coverage']='Federal finance data not supplied' if c['federal_gap'] else ('No matched finance reports' if not reps else ('Candidate reports only; committee match unresolved' if not c['has_committee'] else 'Matched filings; committee mapping subject to review'))
 c['last_submitted']=max([r['SubmittedDate'] for r in reps],default=None)
 c['dc_donor_count']=sum(any(d['connections'] for d in g['transactions']) for g in groups.values())
 if not c['has_committee'] or c['federal_gap']:missing.append({k:c[k] for k in ['id','name','office','district','coverage']})
 report_public=[{k:r[k] for k in ['CampaignfinanceID','FILERID','EYEAR','CYCLE','AMMEND','SubmittedDate','FILERNAME','MONETARY','INKIND']} for r in reps]
 payload=dict(candidate=c,donors=sorted(groups.values(),key=lambda g:g['name'].upper()),reports=report_public)
 (ROOT/f"docs/data/{c['id']}.json").write_text(json.dumps(payload,separators=(',',':')))
 count+=len(records)
for e in entities:e.pop('_aliases')
quality=json.load(open(WORK/'quality.json'))
meta=dict(title='Pennsylvania donor records',as_of='2026-09-15',candidates=cs,entities=entities,coverage_gaps=missing,quality={k:v for k,v in quality.items() if k!='superseded'},superseded_report_count=len(quality['superseded']),candidate_source_rows=232,unique_candidates=len(cs),total_transactions=count,source='Pennsylvania Department of State annual archives supplied by the user',source_url='https://www.pa.gov/agencies/dos/resources/voting-and-elections-resources/campaign-finance-data',readme='https://www.pa.gov/agencies/dos/resources/voting-and-elections-resources/campaign-finance-resources/technical-specifications-for-electronic-filing-of-campaign-expen')
(ROOT/'docs/data/index.json').write_text(json.dumps(meta,separators=(',',':')))
(ROOT/'research/candidate_mappings.json').write_text(json.dumps(cs,indent=2));(ROOT/'research/coverage_gaps.json').write_text(json.dumps(missing,indent=2));(ROOT/'research/superseded_reports.json').write_text(json.dumps(quality['superseded'],indent=2))
for filename,rows in [('all_donors.csv',donors_out),('documented_connections.csv',matches_out)]:
 with open(ROOT/'research'/filename,'w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print(json.dumps({'candidates':len(cs),'transactions':count,'donor_candidate_groups':len(donors_out),'connection_rows':len(matches_out),'coverage_gaps':len(missing),'superseded':len(quality['superseded'])}))
