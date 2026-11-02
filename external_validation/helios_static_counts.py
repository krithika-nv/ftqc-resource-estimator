"""NON-EXECUTING static Python pickle interpreter for the Helios MCMR record.

No vendor modules or pickle.load. Unsupported opcodes fail closed.
Decoded histogram counts are recomputed from the experiment `results` field.
"""
import pickletools,struct,collections,sys
import argparse,json,hashlib
from pathlib import Path
from .core import wilson
class Symbol:
 def __init__(self,name,args=None):self.name=name;self.args=args;self.state=None
 def __repr__(self):return f'Symbol({self.name}, {str(self.state)[:80]})'
M=object()
def parse(raw):
 if len(raw)>20_000_000:raise ValueError('serialized input too large')
 stack=[]; memo={};nextmemo=0
 def popmark():
  j=len(stack)-1
  while stack[j] is not M:j-=1
  vals=stack[j+1:];del stack[j:];return vals
 for op,arg,pos in pickletools.genops(raw):
  n=op.name
  if n in ('PROTO','FRAME'):continue
  if n=='MARK':stack.append(M)
  elif n in ('EMPTY_DICT','EMPTY_LIST','EMPTY_TUPLE','EMPTY_SET'):stack.append({} if n=='EMPTY_DICT' else [] if n=='EMPTY_LIST' else () if n=='EMPTY_TUPLE' else set())
  elif n in ('BININT','BININT1','BININT2','LONG','LONG1','LONG4','BINFLOAT','FLOAT','SHORT_BINUNICODE','BINUNICODE','BINUNICODE8','BINBYTES','SHORT_BINBYTES','BINBYTES8','UNICODE','STRING','BINSTRING','SHORT_BINSTRING','BYTEARRAY8'):stack.append(arg)
  elif n=='NEWTRUE':stack.append(True)
  elif n=='NEWFALSE':stack.append(False)
  elif n=='NONE':stack.append(None)
  elif n=='MEMOIZE':memo[nextmemo]=stack[-1];nextmemo+=1
  elif n in ('BINPUT','LONG_BINPUT','PUT'):memo[int(arg)]=stack[-1]
  elif n in ('BINGET','LONG_BINGET','GET'):stack.append(memo[int(arg)])
  elif n=='STACK_GLOBAL':name=stack.pop();module=stack.pop();stack.append(Symbol(module+'.'+name))
  elif n=='GLOBAL':stack.append(Symbol(str(arg).replace(' ','.')))
  elif n=='TUPLE':stack.append(tuple(popmark()))
  elif n=='TUPLE1':stack.append((stack.pop(),))
  elif n=='TUPLE2':b=stack.pop();a=stack.pop();stack.append((a,b))
  elif n=='TUPLE3':c=stack.pop();b=stack.pop();a=stack.pop();stack.append((a,b,c))
  elif n=='LIST':stack.append(popmark())
  elif n=='DICT':vals=popmark();stack.append(dict(zip(vals[::2],vals[1::2])))
  elif n=='SETITEM':v=stack.pop();k=stack.pop();stack[-1][k]=v
  elif n=='SETITEMS':vals=popmark();stack[-1].update(zip(vals[::2],vals[1::2]))
  elif n=='APPEND':v=stack.pop();stack[-1].append(v)
  elif n=='APPENDS':vals=popmark();stack[-1].extend(vals)
  elif n=='NEWOBJ':args=stack.pop();cls=stack.pop();stack.append(Symbol(cls.name,args))
  elif n=='REDUCE':args=stack.pop();fn=stack.pop();stack.append(Symbol(fn.name,args))
  elif n=='BUILD':state=stack.pop();stack[-1].state=state
  elif n=='STOP':return stack.pop()
  else:raise ValueError(f'unknown opcode {n} at {pos}')
 raise ValueError('missing STOP')


def recover_counts(path:Path):
    if path.stat().st_size>20_000_000:raise ValueError('Helios input above safe static-parser limit')
    raw=path.read_bytes()
    obj=parse(raw)
    if not isinstance(obj,Symbol) or obj.name!='mcmr_crosstalk_comp_basis.MCMR_Crosstalk_Comp_Basis_Experiment':
        raise ValueError('unrecognized Helios experiment class; fail closed')
    attrs=obj.state
    if attrs.get('n_qubits')!=98 or attrs.get('seq_lengths')!=[1,100] or attrs.get('shots')!=1000:
        raise ValueError('unexpected experimental protocol')
    probe=attrs['probe_qubits'];raw_results=attrs['results'];cached=attrs['marginal_results']
    if len(probe)!=90 or len(cached)!=90 or len(raw_results)!=4:raise ValueError('unexpected probe geometry')
    rows=[];matches=0
    for idx,q in enumerate(probe):
        for setting,hist in raw_results.items():
            if not (isinstance(setting,tuple) and len(setting)==3 and len(setting[2])==98):
                raise ValueError('bad experimental setting')
            counts={}
            for bitstring,n in hist.items():
                if not isinstance(bitstring,str) or len(bitstring)!=98 or any(b not in '012' for b in bitstring):
                    raise ValueError('unexpected raw bitstring or atom loss symbol')
                if type(n)!=int or n<0:raise ValueError('invalid hardware shot count')
                b=bitstring[q];counts[b]=counts.get(b,0)+n
            if counts!=cached[idx][(setting[0],setting[1],setting[2][q])]:
                raise ValueError('raw data disagree with author-saved marginal histogram')
            matches+=1
            shots=sum(counts.values())
            if shots!=attrs['shots']:raise ValueError('raw MCMR histogram shot count mismatch')
            survival=counts.get(setting[2][q],0)
            leak=counts.get('2',0)
            rows.append({'qubit':q,'sequence_length':setting[0],'prepared_state':setting[1],
              'expected_outcome':setting[2][q],'successes':survival,'leakage_shots':leak,'shots':shots,
              'survival_rate':survival/shots,'survival_wilson95':wilson(survival,shots)['ci95'],
              'leakage_rate':leak/shots})
    return {'schema':'ftqc.helios.raw-histogram-reanalysis.v1','source_sha256':hashlib.sha256(raw).hexdigest(),
      'experiment':'Helios-1 MCMR crosstalk','hardware':'Helios-1','total_conditions':len(rows),
      'source_raw_histograms':len(raw_results),'original_shots_per_circuit':attrs['shots'],
      'reconstructed_author_marginals_verified':matches,'counts_recalculated_from_original_bitstring_histograms':True,
      'published_global_infidelity_reproduced':False,
      'limitations':['Observed shot counts and survival/leakage rates are independently recomputed from the serialized raw results.',
       'Authors global infidelity requires their weighted constrained fits, NOT a raw proportion or two-point slope.',
       'Static pickle opcodes are interpreted as inert data, never executed; only this exact Helios class/protocol is accepted.',
       'MCMR crosstalk is not measured universal logical-QEC gate fidelity or full FTQC prediction.'],
      'conditions':rows}

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();r=recover_counts(a.input);a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(r,indent=2)+'\n');print('Independently recovered raw Helios counts:',r['total_conditions'])
if __name__=='__main__':main()
