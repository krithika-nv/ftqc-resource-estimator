"""Explicit, checksum-verified open IBM experimental archive download."""
import argparse
import hashlib
from pathlib import Path
import urllib.request

ARCHIVES={
 'ibm_fez':('https://zenodo.org/records/20768087/files/ibm_fez.tar.gz?download=1','27ce2827dde0713a436179121bfd7173'),
 'ibm_kingston':('https://zenodo.org/records/20768087/files/ibm_kingston.tar.gz?download=1','7ed09b461e962c174cedb6c7ee44018b'),
 'ibm_pittsburgh':('https://zenodo.org/records/20768087/files/ibm_pittsburgh.tar.gz?download=1','be1614be0ab19664517b760a8b2bf5bd'),
}
ROOT=Path(__file__).resolve().parents[2]
def download(backend,output):
    url,expected=ARCHIVES[backend]
    if output.is_file():
        existing=hashlib.md5()
        with output.open('rb') as check:
            for part in iter(lambda:check.read(1024*1024),b''): existing.update(part)
        if existing.hexdigest()!=expected:
            raise ValueError('Existing archive checksum does not match Zenodo: '+str(output))
        return str(output)
    output.parent.mkdir(parents=True,exist_ok=True)
    temp=output.with_name(output.name+'.partial')
    digest=hashlib.md5()
    try:
        with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'FTQC-Analysis-Importer/1.1'}),timeout=50) as stream, temp.open('wb') as handle:
            while chunk:=stream.read(1024*1024):
                digest.update(chunk);handle.write(chunk)
        if digest.hexdigest()!=expected:raise ValueError('Zenodo published MD5 does not match downloaded archive; rejecting file')
        temp.replace(output)
    finally:
        temp.unlink(missing_ok=True)
    return str(output)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--backend',choices=sorted(ARCHIVES),default='ibm_fez');p.add_argument('--output',type=Path)
    a=p.parse_args();out=a.output or ROOT/'data/public_calibrations/2026'/(a.backend+'.tar.gz')
    print('Download complete with verified Zenodo MD5:',download(a.backend,out))
