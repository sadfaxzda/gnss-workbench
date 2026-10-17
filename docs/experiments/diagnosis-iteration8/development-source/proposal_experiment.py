from dataclasses import replace
from math import log
from gnss_workbench.core.solver import PositioningEngine
from gnss_workbench.core.diagnosis import AmbiguityResolver

class CoherentEngine(PositioningEngine):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        original_observe=self._ambiguity.observe
        def observe(*a,**kw):
            original=original_observe(*a,**kw)
            temporal=self._temporal_evidence
            if temporal is None or not temporal.detected or original.selected is not None:return original
            keys=tuple(sorted(a[2]))
            if keys!=temporal.keys:return original
            winner,shares,ratio=AmbiguityResolver._compare(temporal.statistics)
            key=keys[winner]; current=min(a[2],key=a[2].get)
            if ratio<log(self.config.fde_likelihood_ratio) or not temporal.passing[winner] or key not in a[3] or .5*(a[2][key]-a[2][current])>=log(self.config.fde_likelihood_ratio):return original
            confirmed=False
            return replace(original,selected=key if confirmed else None,method='coherent_likelihood' if confirmed else 'unresolved',tentative=key,tentative_source='coherent_proposal',epochs=temporal.epochs,start_time=temporal.start_time,log_ratio=ratio,window_shares=dict(zip(keys,map(float,shares),strict=True)))
        self._ambiguity.observe=observe
