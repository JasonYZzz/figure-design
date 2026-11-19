#!/usr/bin/env python3
"""Build an installable DSH tarball from the public Figure Design skill bundle."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import yaml

REPO = Path(__file__).resolve().parents[1]
PLUGIN = REPO / 'plugins/dsh-figure-design'
sys.path.insert(0, str(REPO / 'skills/figure-design/scripts'))
from figure import pack
from figure_common import SKILL_NAME, VERSION, file_hash, read, write


def package_dsh(dist):
    manifest = read(PLUGIN / 'package.json')
    manifest['version'] = VERSION
    out = dist / f"{manifest['name']}-{VERSION}.tgz"
    if out.exists():
        raise FileExistsError(f'package already exists: {out}')
    dist.mkdir(parents=True, exist_ok=True)

    with TemporaryDirectory(prefix='.figure-dsh-', dir=dist) as tmp:
        stage = Path(tmp).resolve()
        bundle = stage / 'bundle'
        shutil.copytree(PLUGIN, bundle, ignore=shutil.ignore_patterns('node_modules', '.DS_Store'))
        write(bundle / 'package.json', manifest)
        for filename in ('LICENSE', 'THIRD_PARTY_NOTICES.md'):
            shutil.copyfile(REPO / filename, bundle / filename)

        public_zip = stage / 'skill.zip'
        pack(public_zip)
        with ZipFile(public_zip) as archive:
            archive.extractall(bundle / 'skills')
        skill_dir = bundle / 'skills' / SKILL_NAME
        skill_text = (skill_dir / 'SKILL.md').read_text(encoding='utf-8')
        header = re.match(r'^---\n(.*?)\n---(?:\n|$)', skill_text, re.DOTALL)
        frontmatter = yaml.safe_load(header[1]) if header else None
        if not isinstance(frontmatter, dict) or frontmatter.get('name') != SKILL_NAME:
            raise ValueError('invalid Figure Design skill metadata')
        description = frontmatter.get('description')
        model_disabled = frontmatter.get('disable-model-invocation', False)
        user_invocable = frontmatter.get('user-invocable', True)
        if not isinstance(description, str) or not description.strip():
            raise ValueError('Figure Design skill requires a description')
        if not isinstance(model_disabled, bool) or not isinstance(user_invocable, bool):
            raise ValueError('Figure Design skill invocation settings must be booleans')
        write(bundle / 'skill.json', {
            'name': SKILL_NAME,
            'description': description,
            'invocation': {
                'modelInvocable': not model_disabled,
                'userInvocable': user_invocable,
            },
        })

        subprocess.run(
            ['npm', 'pack', '--ignore-scripts', '--pack-destination', str(stage)],
            cwd=bundle, check=True, capture_output=True, text=True,
        )
        tgz = stage / out.name
        with tarfile.open(tgz, 'r:gz') as archive:
            files = {entry.name.removeprefix('package/') for entry in archive if entry.isfile()}
        patch = manifest['dsh']['bundle']['patch'].removeprefix('./')
        entry = manifest['exports']['.'].removeprefix('./')
        icon = manifest['exports']['./icon'].removeprefix('./')
        if not {patch, entry, icon, 'locale/en.json', 'locale/zh.json', 'README.md',
                'package.json', 'skill.json', 'LICENSE', 'THIRD_PARTY_NOTICES.md'} <= files:
            raise ValueError('npm pack omitted DSH bundle files')
        rows = yaml.safe_load((bundle / patch).read_text(encoding='utf-8'))
        if [row['name'] for layer in rows for row in layer['insert']] != [manifest['name']]:
            raise ValueError('Cordis patch must load the built bundle by its package name')
        expected = {
            f'skills/{SKILL_NAME}/{path}'
            for path in read(skill_dir / 'package-manifest.json')['files']
        }
        expected.add(f'skills/{SKILL_NAME}/package-manifest.json')
        if {path for path in files if path.startswith('skills/')} != expected:
            raise ValueError('npm pack changed the public skill file list')
        os.link(tgz, out)
    return {'package': str(out), 'version': VERSION, 'sha256': file_hash(out), 'files': len(files)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dist', required=True, type=Path)
    args = parser.parse_args()
    try:
        print(json.dumps(package_dsh(args.dist), ensure_ascii=False, indent=2))
    except subprocess.CalledProcessError as exc:
        parser.exit(2, exc.stderr or str(exc) + '\n')
    except (OSError, ValueError) as exc:
        parser.exit(2, str(exc) + '\n')
