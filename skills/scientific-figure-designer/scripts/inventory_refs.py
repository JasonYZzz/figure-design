#!/usr/bin/env python3
"""Read-only inventory for local reference images. This does NOT extract assets or grant reuse rights.

Requires Pillow (pip install Pillow). Output paths are relative to input root.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
import warnings
from PIL import Image, ImageOps, UnidentifiedImageError

EXTS={'.png','.jpg','.jpeg','.webp','.bmp','.tif','.tiff','.gif'}

def digest(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):
            h.update(block)
    return h.hexdigest()

def dhash64(image:Image.Image)->str:
    gray=ImageOps.exif_transpose(image).convert('L').resize((9,8),Image.Resampling.LANCZOS)
    pix=list(gray.get_flattened_data() if hasattr(gray, "get_flattened_data") else gray.getdata()); value=0
    for y in range(8):
        for x in range(8):
            value=(value<<1)|(1 if pix[y*9+x]>pix[y*9+x+1] else 0)
    return f'{value:016x}'

def inventory(root:Path)->tuple[list[dict],list[dict]]:
    root=root.resolve()
    if not root.is_dir(): raise ValueError(f'No input directory: {root}')
    files=sorted((p for p in root.rglob('*') if p.is_symlink() or (p.is_file() and p.suffix.lower() in EXTS)),key=lambda p:p.relative_to(root).as_posix())
    seen={}; records=[]; errors=[]
    for index,path in enumerate(files,1):
        rel=path.relative_to(root).as_posix()
        if path.is_symlink():
            errors.append({'path':rel,'error':'Symbolic links are not followed'})
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('error', Image.DecompressionBombWarning)
                with Image.open(path) as image:
                    image.verify()
                with Image.open(path) as image:
                    oriented=ImageOps.exif_transpose(image)
                    w,h=oriented.size
                    ph=dhash64(image)
            checksum=digest(path)
            records.append({
                'id':f'ref_{index:04d}','path':rel,'sha256':checksum,'width':w,'height':h,
                'dhash64':ph,'exact_duplicate_of':seen.get(checksum),
                'domain_tags':[],'figure_type_tags':[],'composition_tags':[],
                'text_density':'unknown','asset_tags':[],
                'license_state':'unknown','review_status':'unreviewed','origin':None,'notes':''
            })
            seen.setdefault(checksum,f'ref_{index:04d}')
        except (OSError,ValueError,SyntaxError,UnidentifiedImageError,Image.DecompressionBombError,Image.DecompressionBombWarning) as exc:
            errors.append({'path':rel,'error':type(exc).__name__+': '+str(exc)[:160]})
    return records,errors

def atomic_write(path:Path,text:str)->None:
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,delete=False) as stream:
            temporary=Path(stream.name)
            stream.write(text)
        os.replace(temporary,path)
    finally:
        if temporary is not None:temporary.unlink(missing_ok=True)

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',required=True,type=Path)
    p.add_argument('--out',required=True,type=Path)
    p.add_argument('--expected-count',type=int,default=0)
    args=p.parse_args()
    if args.expected_count<0:p.error('expected-count must be nonnegative')
    root=args.input.resolve()
    outputs=[args.out,args.out.with_suffix('.errors.json')]
    if any(path.resolve()==root or root in path.resolve().parents for path in outputs):
        p.error('Output must be outside the input directory; refusing to overwrite originals')
    try:
        records,errors=inventory(args.input)
        args.out.parent.mkdir(parents=True,exist_ok=True)
        atomic_write(args.out,''.join(json.dumps(record,ensure_ascii=False,sort_keys=True)+'\n' for record in records))
        atomic_write(outputs[1],json.dumps(errors,ensure_ascii=False,indent=2)+'\n')
    except (OSError,ValueError) as exc:
        p.error(str(exc))
    summary={'valid_images':len(records),'errors':len(errors),'exact_duplicates':sum(bool(x['exact_duplicate_of']) for x in records),'count_matches':(len(records)==args.expected_count if args.expected_count else None),'out':str(args.out)}
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    return 2 if errors or (args.expected_count and len(records)!=args.expected_count) else 0

if __name__=='__main__': raise SystemExit(main())
