"""Plot-exact-value reconstruction of Aurora supplementary Fig 3c/3d tables.

This is *figure-data reproduction* from the publisher-supplied workbook, NOT an
independent re-analysis of the large optical homodyne measurement files.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,math
from pathlib import Path

LABELS={
 'Fig 3c':['experimental X measurement','experimental Z measurement',
           'simulated X measurement','simulated Z measurement'],
 'Fig 3d':['experimental feedforward','experimental no feedforward',
           'simulated feedforward','simulated no feedforward'],
}

def reproduce(workbook:Path,output:Path,figure='both',plot=True):
    from openpyxl import load_workbook
    if not workbook.is_file():raise FileNotFoundError(workbook)
    sha=hashlib.sha256(workbook.read_bytes()).hexdigest()
    wb=load_workbook(workbook,read_only=True,data_only=True)
    wanted=list(LABELS) if figure=='both' else [figure]
    output.mkdir(parents=True,exist_ok=True)
    results={}
    try:
        for sheet in wanted:
            if sheet not in wb.sheetnames:raise ValueError(f'Workbook lacks {sheet!r}: {wb.sheetnames}')
            rows=list(wb[sheet].values)
            if len(rows)<3:raise ValueError(f'{sheet}: missing header or numeric grid')
            header=tuple(str(v).strip().lower() if v is not None else '' for v in rows[1][:6])
            expected=['row','column']+[s.split(' ',1)[1] for s in LABELS[sheet]]
            # Some column headings repeat as merged headers; validate the first
            # row/column and the presence of precisely four numerical matrices.
            if header[:2]!=('row','column'):
                raise ValueError(f'{sheet}: unrecognized row/column headers: {header}')
            records=[]
            for i,row in enumerate(rows[2:],start=3):
                if not any(v is not None for v in row[:6]):continue
                if len(row)<6 or any(v is None for v in row[:6]):
                    raise ValueError(f'{sheet} row {i}: incomplete six-column matrix record')
                vals=[float(v) for v in row[:6]]
                if any(not math.isfinite(v) for v in vals):
                    raise ValueError(f'{sheet} row {i}: non-finite matrix element')
                r,c=vals[:2]
                if int(r)!=r or int(c)!=c or r<0 or c<0:
                    raise ValueError(f'{sheet} row {i}: invalid matrix coordinate {r,c}')
                records.append((int(r),int(c),*vals[2:]))
            if not records:raise ValueError(f'{sheet}: no experimental data')
            size=max(max(r,c) for r,c,*_ in records)+1
            if size>128:raise ValueError('Unexpected matrix dimensions')
            if len(records)!=size*size or len({(r,c) for r,c,*_ in records})!=size*size:
                raise ValueError(f'{sheet}: incomplete/duplicate {size}x{size} matrix grid')
            # Full experiment/simulation matrix values come from the workbook,
            # not synthetic values or estimated image pixels.
            matrices=[[[0.0]*size for _ in range(size)] for _ in range(4)]
            for r,c,*values in records:
                for k,v in enumerate(values):matrices[k][r][c]=v
            def residual(a,b):
                delta=[x-y for ar,br in zip(a,b) for x,y in zip(ar,br)]
                reference=[x for ar in a for x in ar]
                n=len(delta)
                return {'mean_absolute_difference':sum(abs(x) for x in delta)/n,
                        'rmse':math.sqrt(sum(x*x for x in delta)/n),
                        'max_absolute_difference':max(abs(x) for x in delta),
                        'relative_frobenius':math.sqrt(sum(x*x for x in delta))/math.sqrt(sum(x*x for x in reference)) if any(reference) else None}
            stats={'panel_1_experiment_vs_simulation':residual(matrices[0],matrices[2]),
                   'panel_2_experiment_vs_simulation':residual(matrices[1],matrices[3])}
            with (output/(sheet.replace(' ','_')+'_matrix_data.csv')).open('w',newline='') as f:
                w=csv.writer(f);w.writerow(['row','column',*LABELS[sheet]]);w.writerows(records)
            if plot:
                import matplotlib
                matplotlib.use('Agg')
                import matplotlib.pyplot as plt
                fig,axes=plt.subplots(1,4,figsize=(15,4),constrained_layout=True)
                max_abs=max(abs(v) for matrix in matrices for line in matrix for v in line)
                for ax,arr,label in zip(axes,matrices,LABELS[sheet]):
                    im=ax.imshow(arr,cmap='coolwarm',vmin=-max_abs,vmax=max_abs,interpolation='nearest',origin='upper')
                    ax.set_title(label,fontsize=9);ax.set_xlabel('column');ax.set_ylabel('row')
                fig.colorbar(im,ax=axes,label='published matrix value',shrink=.72)
                fig.suptitle(f'Aurora {sheet}: replot of published numerical data',fontsize=12)
                fig.savefig(output/(sheet.replace(' ','_')+'_replot.png'),dpi=180)
                plt.close(fig)
            results[sheet]={'size':size,'entries':len(records),'labels':LABELS[sheet],
                            'experiment_vs_simulation':stats,
                            'data_csv':sheet.replace(' ','_')+'_matrix_data.csv',
                            'figure':sheet.replace(' ','_')+'_replot.png' if plot else None}
    finally:wb.close()
    report={'status':'complete_figure_data_replot','source_url':'https://github.com/XanaduAI/xanadu-aurora-data',
            'workbook_sha256':sha,'workbook_path':str(workbook),'reproductions':results,
            'limitations':['This replots the paper-supplied matrix numbers; it is not an independent reconstruction from raw quadrature samples.',
                           'No uncertainty is inferred because the supplied matrix values do not contain shot-level uncertainty information.',
                           'The original Nature figure layout is not asserted identical to the new plot.']}
    (output/'REPORT.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,default=Path('outputs/external_validation/aurora_reproduction'))
    p.add_argument('--figure',choices=['Fig 3c','Fig 3d','both'],default='both')
    p.add_argument('--no-plot',action='store_true');a=p.parse_args()
    try:
        result=reproduce(a.input,a.output_dir,figure=a.figure,plot=not a.no_plot)
        print(json.dumps({'status':result['status'],'plots':list(result['reproductions']),'output_dir':str(a.output_dir)}))
    except Exception as e:
        p.exit(2,f'ERROR: {e}\n')
if __name__=='__main__':main()
