"""Independent offline audit of a documented toy model.

Output file can be regenerated from this script with PYTHONPATH=src.
"""
import json
from pathlib import Path

from ftqc_resource_estimator.model import Scenario
from ftqc_resource_estimator.pareto import frontier
base_args=dict(physical_error=.001,threshold_assumption=.01,prefactor=.1)
a=Scenario('reference',cycle_microseconds=1.,decode_microseconds=5.,**base_args)
b=Scenario('fast_cycle_slow_decoder',cycle_microseconds=.35,decode_microseconds=9.,**base_args)
rows=frontier([a,b],[3,5,7,9,11],10,1000,.01)
data={'model':'illustrative logical error ansatz, identical chosen coefficients, NOT physical hardware','logical_qubits':10,'operations':1000,'target_failure':.01,'pareto':[{'scenario':x.scenario,'distance':x.distance,'sites':x.physical_sites,'latency_us':x.latency_microseconds,'modeled_failure':x.total_failure_probability} for x in rows]}

out=Path('examples/generated/development_audit.json')
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
print(out)
print(json.dumps(data,indent=2))
