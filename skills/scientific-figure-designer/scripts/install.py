#!/usr/bin/env python3
"""Install an extracted, manifest-verified skill without overwriting existing work."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile


def install(source, destination):
    source=Path(source).resolve();destination=Path(destination).expanduser().resolve()
    target=destination/'scientific-figure-designer'
    if target.exists():raise ValueError('target exists; compare or back up the old version before installing')
    manifest=json.loads((source/'package-manifest.json').read_text(encoding='utf-8'))
    expected=set(manifest['files'])|{'package-manifest.json'}
    for relative,digest in manifest['files'].items():
        path=(source/relative).resolve()
        if not path.is_relative_to(source) or (source/relative).is_symlink():raise ValueError('unsafe package path')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('package hash mismatch: '+relative)
    actual={p.relative_to(source).as_posix() for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.name!='.DS_Store'}
    if actual!=expected:raise ValueError('unexpected or missing package files')
    destination.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='.figure-install-',dir=destination))
    try:
        for relative in expected:
            path=stage/relative;path.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/relative,path)
        if target.exists():raise ValueError('target appeared during install')
        stage.rename(target)
    finally:
        if stage.exists():shutil.rmtree(stage)
    return target


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--to',required=True,help='Skills parent, e.g. ~/.agents/skills or PROJECT/.agents/skills')
    a=p.parse_args()
    try:print(install(Path(__file__).resolve().parents[1],a.to))
    except (ValueError,OSError,KeyError) as exc:p.exit(2,str(exc)+'\n')
