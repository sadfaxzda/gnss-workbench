from pathlib import Path
import json,csv,sys
import numpy as np
from dataclasses import asdict
from gnss_workbench.core.models import SolverConfig
from gnss_workbench.core.solver import PositioningEngine
from gnss_workbench.core.coordinates import local_enu
from gnss_workbench.io import navigation_from,read_epochs
from gnss_workbench.settings import COURSE_ROOT
sys.path.insert(0,str(Path('scripts').resolve()))
from validate_six_satellite import summarize
suite=sys.argv[1]
source=Path('runtime/diagnosis-iteration6')/('final-'+suite)
out=Path('runtime/diagnosis-iteration8')/('dev-proposal-'+suite)
out.mkdir(exist_ok=False)
nav=navigation_from(COURSE_ROOT/'data/navigation.json')
from proposal_experiment import CoherentEngine
configs={'proposal':SolverConfig()}
groups={}
for ci,folder in enumerate(sorted(source.iterdir())):
 if not (folder/'input.jsonl').is_file():continue
 old=json.loads((folder/'new/evaluation.json').read_text())
 truth=list(csv.DictReader((folder/'truth.csv').open()))
 frames=list(read_epochs(folder/'input.jsonl'))
 kind=folder.name.split('-',2)[-1] if suite!='irregular' else folder.name.split('-',1)[-1]
 dest=out/folder.name;dest.mkdir()
 for method,config in configs.items():
  engine=CoherentEngine(nav,config)
  records=[]
  with (dest/(method+'-diagnostics.jsonl')).open('w') as logs:
   for epoch,label,original in zip(frames,truth,old,strict=True):
    _,s=engine.solve(epoch)
    logs.write(json.dumps(s.to_dict(),ensure_ascii=False,allow_nan=False)+'\n')
    xyz=np.array([float(label[k]) for k in ['x_m','y_m','z_m']])
    err=float(np.linalg.norm(local_enu(np.array([s.x_m,s.y_m,s.z_m]),xyz)[:2])) if s.has_position else None
    row=dict(original)
    correct=bool(row['fault_satellite'] and row['fault_satellite'] in s.flagged_sats)
    wrong=bool(set(s.excluded_sats)-{row['fault_satellite']})
    row.update(horizontal_error_m=err,clock_error_m=abs(s.clock_bias_m-float(label['clock_bias_m'])) if s.has_position else None,correct_flag=correct,confirmed_correct=correct and s.status=='FAULT_EXCLUDED',wrong_exclusion=wrong,confirmed_wrong=wrong and s.status=='FAULT_EXCLUDED',provisional=s.status=='SUSPECT' and bool(s.excluded_sats),status=s.status,flagged=s.flagged_sats,excluded=s.excluded_sats)
    records.append(row)
  (dest/(method+'-evaluation.json')).write_text(json.dumps(records))
  groups.setdefault(kind+'/'+method,[]).extend(records)
  groups.setdefault('all/'+method,[]).extend(records)
 groups.setdefault(kind+'/previous',[]).extend(old)
 groups.setdefault('all/previous',[]).extend(old)
 if ci%14==0:print(suite,ci,flush=True)
summary={k:summarize(v) for k,v in groups.items()}
(out/'metrics.json').write_text(json.dumps(summary,indent=2))
(out/'configurations.json').write_text(json.dumps({k:asdict(v) for k,v in configs.items()},indent=2))
print(json.dumps({k:{m:v[m] for m in ['h_p95_m','fault_only_h_p95_m','fault_only_success10','wrong_exclusions','confirmed_wrong_exclusions','clean_false_alarm_rate']} for k,v in summary.items()},indent=2),flush=True)
