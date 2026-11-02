"""Read-only photonic numerical analyses; no source paper figures fabricated.

GKP reconstructed density-matrix diagnostic uses the standard photon-number
parity Wigner convention W(0) = (2/pi) Tr[rho (-1)^n].  The source GKP
analysis_results.npy may have a structured/object format; object pickle is
never silently loaded. In that case use an upstream-trusted numeric export.
"""
from __future__ import annotations
import argparse
from math import pi, isfinite
from pathlib import Path
from .evidence_analysis import file_hash, save_report, number


def analyze_density_matrix(path:Path, *, atol:float=1e-6) -> dict:
    import numpy as np
    try:
        raw=np.load(path,allow_pickle=False)
    except ValueError as exc:
        raise ValueError('Density-matrix input must be a plain numeric .npy, not an object/pickle array; use a trusted upstream numeric export') from exc
    if raw.ndim!=2 or raw.shape[0]!=raw.shape[1] or raw.shape[0]<2 or raw.shape[0]>4096:
        raise ValueError('need a finite square density matrix, dimension 2..4096')
    if not np.issubdtype(raw.dtype,np.number):raise ValueError('nonnumeric density matrix')
    rho=np.asarray(raw,dtype=np.complex128)
    if not np.isfinite(rho).all():raise ValueError('nonfinite density matrix')
    herm=float(np.max(np.abs(rho-rho.conj().T)))
    trace=complex(np.trace(rho))
    eig=np.linalg.eigvalsh((rho+rho.conj().T)/2)
    if herm>atol or abs(trace-1)>atol or eig[0]<-atol:
        raise ValueError(f'invalid density matrix: Hermitian discrepancy={herm}, trace={trace}, min eig={eig[0]}')
    purity=float(np.real(np.trace(rho@rho)))
    p=np.real(np.diag(rho))
    return {'scope':'GKP_RECONSTRUCTED_STATE_DIAGNOSTIC_NOT_SOURCE_FIGURE_REPRODUCTION',
      'source_file_sha256':file_hash(path),'fock_cutoff':len(rho),
      'trace':float(trace.real),'hermiticity_residual':herm,
      'smallest_eigenvalue':float(eig[0]),'purity':purity,
      'wigner_origin_parity_convention':float(2/pi*sum(((-1)**n)*v for n,v in enumerate(p))),
      'mean_photon_number_within_cutoff':float(sum(n*v for n,v in enumerate(p))),
      'truncation_warning':'Physical state outside this Fock cutoff is not observed; input is an upstream reconstruction, not raw homodyne shots.',
      'citation':'https://github.com/XanaduAI/xanadu-gkp-data'}


def aurora_figure_from_workbook(path:Path, sheet:str, x_col:str, y_col:str, *, unit:str, reported_reference:float|None=None):
    """Extract source-workbook columns with explicit analyst-selected fields; no implicit figure equivalence."""
    from openpyxl import load_workbook
    wb=load_workbook(path,read_only=True,data_only=True)
    if sheet not in wb.sheetnames:raise ValueError(f'unknown sheet {sheet}; available {wb.sheetnames}')
    ws=wb[sheet]; it=ws.iter_rows(values_only=True)
    header=next(it,None)
    if not header or x_col not in header or y_col not in header:raise ValueError('explicit x and y column headers required')
    ix=header.index(x_col); iy=header.index(y_col)
    pairs=[]
    for cells in it:
        if len(cells)<=max(ix,iy) or cells[ix] is None or cells[iy] is None:continue
        try: y=number(cells[iy],y_col)
        except ValueError: continue
        pairs.append([str(cells[ix]),y])
    if not pairs: raise ValueError('no numeric source figure data')
    return {'scope':'ORIGINAL_AURORA_WORKBOOK_COLUMN_EXTRACTION_NOT_PAPER_FIGURE_VALIDATION',
        'source_file_sha256':file_hash(path),'sheet':sheet,'x_column':x_col,'y_column':y_col,
        'y_unit':unit,'source_points':pairs,'point_count':len(pairs),
        'reported_reference':reported_reference,
        'comparison':'NOT_COMPUTED: reference point identity/measurement provenance must be specified',
        'citation':'https://github.com/XanaduAI/xanadu-aurora-data'}


def main():
    p=argparse.ArgumentParser(description='Source-specific photonic numerical analysis')
    sub=p.add_subparsers(dest='mode',required=True)
    g=sub.add_parser('gkp');g.add_argument('--density-npy',type=Path,required=True);g.add_argument('--output-dir',type=Path,required=True)
    a=sub.add_parser('aurora');a.add_argument('--workbook',type=Path,required=True);a.add_argument('--sheet',required=True)
    a.add_argument('--x-column',required=True);a.add_argument('--y-column',required=True);a.add_argument('--unit',required=True)
    a.add_argument('--output-dir',type=Path,required=True)
    v=p.parse_args()
    if v.mode=='gkp':result=analyze_density_matrix(v.density_npy)
    else:result=aurora_figure_from_workbook(v.workbook,v.sheet,v.x_column,v.y_column,unit=v.unit)
    save_report(v.output_dir,'PHOTONIC_NUMERICAL_ANALYSIS',result,'A source-data analysis only; this is not a hardware-calibrated FTQC model or verified published figure reproduction.')
    print(f"Photonic numerical analysis generated: {v.output_dir}; scope={result['scope']}")
if __name__=='__main__':main()
