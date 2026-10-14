"""Independent CSV contract and truth-based metric checker (not an automatic final grade).
All mandatory epochs remain in availability/success-rate denominators.
Does not use the reference GNSS engine. NumPy is required only for ENU errors.
"""
from __future__ import annotations
import argparse,csv,json,math
from pathlib import Path
import numpy as np

POSITION_STATES={'VALID','FAULT_EXCLUDED','FAULT_MITIGATED','SUSPECT','NO_REDUNDANCY','GEOMETRY_WARNING'}
INVALID_STATES={'INVALID_INSUFFICIENT','NO_OBSERVATIONS','INVALID_GEOMETRY','INVALID_CONVERGENCE','INVALID_DATA','INVALID_EPHEMERIS'}
ALLOWED=POSITION_STATES|INVALID_STATES
REQUIRED={'epoch_id','gps_week','gps_sow','status','x_m','y_m','z_m','clock_bias_m','n_used','pdop','flagged_sats','excluded_sats','residual_rms_m','processing_ms'}

def finite(row,key):
    try:
        v=float(row[key]);return v if math.isfinite(v) else None
    except (KeyError,ValueError,TypeError):return None

def enu_error(ref,est):
    # Independent geodetic conversion; no import from reference solver.
    x,y,z=ref;p=math.hypot(x,y);lon=math.atan2(y,x);e2=6.6943799901413165e-3
    lat=math.atan2(z,p*(1-e2))
    for _ in range(10):
        N=6378137/math.sqrt(1-e2*math.sin(lat)**2);lat=math.atan2(z+e2*N*math.sin(lat),p)
    sl,cl=math.sin(lon),math.cos(lon);s,c=math.sin(lat),math.cos(lat)
    R=np.array([[-sl,cl,0],[-s*cl,-s*sl,c],[c*cl,c*sl,s]])
    err=R@(np.array(est)-np.array(ref));return float(math.hypot(err[0],err[1])),float(abs(err[2]))

def evaluate(input_path:Path,truth_path:Path,solution_path:Path)->dict:
    inp=[json.loads(s) for s in input_path.read_text(encoding='utf8').splitlines() if s.strip()]
    inp={int(e['epoch_id']):e for e in inp if e['type']=='epoch'}
    truths={int(r['epoch_id']):r for r in csv.DictReader(truth_path.open(encoding='utf-8-sig'))}
    if set(inp)!=set(truths):raise ValueError('Input and truth epoch sets differ')
    reader=csv.DictReader(solution_path.open(encoding='utf-8-sig'))
    if not REQUIRED.issubset(set(reader.fieldnames or [])):raise ValueError('Missing output columns: '+str(REQUIRED-set(reader.fieldnames or [])))
    rows=list(reader);sol={};viol=[]
    def violation(eid,text):viol.append({'epoch_id':eid,'issue':text})
    bad_ids=set()
    for r in rows:
        try:eid=int(r['epoch_id'])
        except (ValueError,KeyError):violation(None,'Invalid epoch_id');continue
        if eid in sol:violation(eid,'Duplicate output row');bad_ids.add(eid)
        sol[eid]=r
    for eid in set(sol)-set(inp):violation(eid,'Unexpected epoch_id');bad_ids.add(eid)
    required=valid=success10=0;he=[];ve=[];ce=[];runt=[]
    strong_fault=detected=excluded_detected=0;clean=fa=fa_excluded=0;invalid_expected=invalid_correct=0;four=four_correct=0;geom=geom_correct=0
    per=[]
    for eid,t in truths.items():
        e=inp[eid];r=sol.get(eid);expected=t['expected_state'];n=len(e['observations']);sats={o['sat_id'] for o in e['observations']}
        need=expected in {'POSITION_REQUIRED','NO_REDUNDANCY'}
        if need:required+=1
        f=t['fault_sat'];fb=float(t['fault_bias_m']);isstrong=bool(f) and abs(fb)>=30
        if isstrong:strong_fault+=1
        if not f and n>=4:clean+=1
        if expected in {'INVALID_INSUFFICIENT','NO_OBSERVATIONS'}:invalid_expected+=1
        if expected=='NO_REDUNDANCY':four+=1
        if expected=='GEOMETRY_WARNING':geom+=1
        if not r:
            violation(eid,'Missing output row');per.append({'epoch_id':eid,'expected':expected,'status':'MISSING'});continue
        status=r['status'];xyz=[finite(r,k) for k in ['x_m','y_m','z_m']];b=finite(r,'clock_bias_m')
        excl=[x for x in r['excluded_sats'].split(';') if x];excluded=set(excl)
        flag=[x for x in r['flagged_sats'].split(';') if x];flagged=set(flag)
        contract_ok=True
        if status not in ALLOWED:violation(eid,'Unknown status');contract_ok=False
        if len(flag)!=len(flagged) or not flagged.issubset(sats):violation(eid,'Invalid flagged satellite list');contract_ok=False
        if len(excl)!=len(excluded) or not excluded.issubset(sats):violation(eid,'Invalid excluded satellite list');contract_ok=False
        try:nused=int(r['n_used'])
        except ValueError:nused=-1
        if nused<0 or nused>n:violation(eid,'Invalid n_used');contract_ok=False
        if finite(r,'gps_sow') is None or abs(float(r['gps_sow'])-e['gps_sow'])>1e-6:violation(eid,'Timestamp mismatch');contract_ok=False
        if str(r['gps_week'])!=str(e['gps_week']):violation(eid,'GPS week mismatch');contract_ok=False
        haspos=all(v is not None for v in xyz) and b is not None
        if status in POSITION_STATES and (not haspos or nused<4 or nused>n-len(excluded)):
            violation(eid,'Position status conflicts with coordinates or satellite count');contract_ok=False
        if status in POSITION_STATES and (finite(r,'pdop') is None or finite(r,'pdop')<=0 or finite(r,'residual_rms_m') is None or finite(r,'residual_rms_m')<0):
            violation(eid,'Missing or invalid PDOP/residual');contract_ok=False
        if status in INVALID_STATES and any((r.get(k) or '').strip() for k in ['x_m','y_m','z_m','clock_bias_m']):
            violation(eid,'Invalid epochs must leave current-fix coordinates blank');contract_ok=False
        if status in POSITION_STATES and n<4:violation(eid,'Fewer than 4 observations reported as independent 3D fix');contract_ok=False
        if eid in bad_ids:contract_ok=False
        h=v=c=None
        if haspos and status in POSITION_STATES and contract_ok:
            ref=[float(t[k]) for k in ['x_m','y_m','z_m']];h,v=enu_error(ref,xyz);c=abs(b-float(t['clock_bias_m']))
            if need:
                valid+=1;he.append(h);ve.append(v);ce.append(c);success10+=int(h<=10)
        if isstrong and f in flagged and contract_ok:detected+=1
        if isstrong and f in excluded and contract_ok:excluded_detected+=1
        if not f and n>=4 and flagged:fa+=1
        if not f and n>=4 and excluded:fa_excluded+=1
        if expected in {'INVALID_INSUFFICIENT','NO_OBSERVATIONS'} and status==expected and contract_ok:invalid_correct+=1
        if expected=='NO_REDUNDANCY' and status=='NO_REDUNDANCY' and contract_ok and haspos:four_correct+=1
        if expected=='GEOMETRY_WARNING' and status in {'GEOMETRY_WARNING','INVALID_GEOMETRY'} and contract_ok:geom_correct+=1
        tm=finite(r,'processing_ms')
        if tm is not None and tm>=0:runt.append(tm)
        per.append({'epoch_id':eid,'expected':expected,'status':status,'h_error_m':h,'v_error_m':v,'clock_error_m':c,'contract_ok':contract_ok})
    def frac(a,b):return a/b if b else None
    def quant(a,p):return float(np.percentile(a,p)) if a else None
    return {'schema':'GNSS-COURSE-EVAL-1.0','input':input_path.name,'solution':solution_path.name,
        'input_epochs':len(inp),'output_rows':len(rows),'position_required_epochs':required,'valid_required_epochs':valid,
        'availability_on_required':frac(valid,required),'success_within_10m_on_required':frac(success10,required),
        'h_median_m':quant(he,50),'h_p95_m':quant(he,95),'v_p95_m':quant(ve,95),'clock_p95_m':quant(ce,95),
        'strong_fault_epochs_bias_ge_30m':strong_fault,'fault_detection_recall':frac(detected,strong_fault),'fault_exclusion_recall':frac(excluded_detected,strong_fault),
        'clean_epochs':clean,'false_alarm_epoch_rate':frac(fa,clean),'false_exclusion_epoch_rate':frac(fa_excluded,clean),'invalid_expected_epochs':invalid_expected,
        'correct_invalid_state_rate':frac(invalid_correct,invalid_expected),'four_satellite_epochs':four,
        'correct_no_redundancy_rate':frac(four_correct,four),'poor_geometry_epochs':geom,'correct_geometry_warning_rate':frac(geom_correct,geom),
        'self_reported_processing_p95_ms':quant(runt,95),'contract_violation_count':len(viol),'contract_violations':viol,
        'notes':['Position-error percentiles are conditional on valid required epochs; always read together with availability and joint success rate.',
                 'Poor-geometry test windows are reported separately and excluded from normal precision thresholds.',
                 'processing_ms is self-reported; use teacher-side wall-clock observation for timing marks.'],
        'per_epoch':per}

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--input',required=True,type=Path);a.add_argument('--truth',required=True,type=Path)
    a.add_argument('--solution',required=True,type=Path);a.add_argument('--out',required=True,type=Path)
    q=a.parse_args();result=evaluate(q.input,q.truth,q.solution);q.out.parent.mkdir(parents=True,exist_ok=True);q.out.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False))
    print(json.dumps({k:v for k,v in result.items() if k not in ['per_epoch','contract_violations']},indent=2,ensure_ascii=False))
