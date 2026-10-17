from dataclasses import replace
from math import log
import numpy as np
from scipy.stats import chi2
from gnss_workbench.core.solver import PositioningEngine
from gnss_workbench.core.diagnosis import AmbiguityResolver

class CoherentEngine(PositioningEngine):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        original_observe=self._ambiguity.observe
        def observe(*a,**kw):
            original=original_observe(*a,**kw)
            temporal=self._temporal_evidence
            if temporal is None or not temporal.detected or original.method=='current_likelihood':return original
            keys=tuple(sorted(a[2]))
            if keys!=temporal.keys:return original
            records=list(self._temporal.samples)[-temporal.epochs:]
            w=np.array([1/max(self._sigma,x[3])**2 for x in records])
            r=np.array([x[1] for x in records]);diagonal=np.array([x[2] for x in records]);dof=len(keys)-4
            aa=(w[:,None]*diagonal).sum(axis=0);z=(w[:,None]*r).sum(axis=0)
            const=np.maximum(0,temporal.null_statistic-z*z/np.maximum(aa,1e-12))
            penalty=log(len(records)*dof)
            use_const=const+penalty<=temporal.statistics+2*penalty
            costs=np.where(use_const,const+penalty,temporal.statistics+2*penalty)
            winner,shares,ratio=AmbiguityResolver._compare(costs)
            key=keys[winner];current=min(a[2],key=a[2].get)
            if not temporal.passing[winner] or key not in a[3] or .5*(a[2][key]-a[2][current])>=log(self.config.fde_likelihood_ratio):return original
            if use_const[winner]:
                old_a=(w[:-1,None]*diagonal[:-1]).sum(axis=0)
                old_z=(w[:-1,None]*r[:-1]).sum(axis=0)
                bias=old_z/np.maximum(old_a,1e-12);var=1/np.maximum(old_a,1e-12);s=diagonal[-1]
                current_stat=float(r[-1]@r[-1]/self._sigma**2)
                innovation=current_stat-2*bias*r[-1]/self._sigma**2+bias*bias*s/self._sigma**2
                innovation-=var*(r[-1]-bias*s)**2/(self._sigma**2*(self._sigma**2+var*s))
                if const[winner]>chi2.isf(self.config.false_alarm_probability,len(records)*dof-1) or innovation[winner]>chi2.isf(self.config.false_alarm_probability,dof):return original
            confirmed=ratio>=log(self.config.fde_likelihood_ratio) and (not self.config.fde_change_detection or current==key)
            return replace(original,selected=key if confirmed else None,method='order_adaptive' if confirmed else 'unresolved',tentative=key,tentative_source='order_adaptive',epochs=temporal.epochs,start_time=temporal.start_time,log_ratio=ratio,window_shares=dict(zip(keys,map(float,shares),strict=True)))
        self._ambiguity.observe=observe
