#!/usr/bin/env python3
"""Build a separate, pixel-verified lossless reference library from the active one."""
import argparse
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
from tempfile import TemporaryDirectory
import zlib

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'skills/figure-design/scripts'))
from figure_catalog import image_files
from figure_common import canonical, file_hash, inside
from figure_knowledge import LIBRARY, WIKI_DIR, build, lint, records
from inventory_refs import inventory


def compact_png(path):
    source = path.read_bytes()
    if source[:8] != b'\x89PNG\r\n\x1a\n' or source[24:25] != b'\x08':
        return None
    with Image.open(io.BytesIO(source)) as im:
        im.load()
        # Preserve ancillary metadata, including signed provenance, in its original container.
        if (im.n_frames != 1 or im.mode not in ('RGB', 'RGBA') or im.private_chunks
                or set(im.info) - {'srgb'} or im.info.get('srgb', 0) != 0):
            return None
        # Chromium can round partially transparent PNG and WebP pixels differently on compositing.
        if im.mode == 'RGBA' and any(im.getchannel('A').histogram()[1:255]):
            return None
        buffer = io.BytesIO()
        im.save(buffer, 'WEBP', lossless=True, exact=True, quality=100, method=6)
        data = buffer.getvalue()
        if len(data) >= len(source) or len(zlib.compress(data, 9)) >= len(zlib.compress(source, 9)):
            return None
        with Image.open(io.BytesIO(data)) as result:
            if result.size != im.size or result.convert('RGBA').tobytes() != im.convert('RGBA').tobytes():
                raise ValueError(f'lossless verification failed for {path.name}')
    return data


def is_lossless_webp(path):
    with path.open('rb') as f:
        header = f.read(12)
        if header[:4] != b'RIFF' or header[8:] != b'WEBP':
            return False
        while len(chunk := f.read(8)) == 8:
            if chunk[:4] == b'VP8L':
                return True
            size = int.from_bytes(chunk[4:], 'little')
            f.seek(size + (size % 2), 1)
    return False


def to_lossless_webp(path):
    """Create a display derivative. The source container remains in the input library."""
    with Image.open(path) as im:
        if getattr(im, 'n_frames', 1) != 1 or im.mode not in ('RGB', 'RGBA', 'L', 'LA', 'P'):
            raise ValueError(f'unsupported image depth, mode or animation: {path.name}')
        if im.format == 'PNG' and path.read_bytes()[24] > 8:
            raise ValueError(f'unsupported PNG depth: {path.name}')
        pixels = im.convert('RGBA')
        buf = io.BytesIO()
        metadata = {k: im.info[k] for k in ('icc_profile', 'exif') if im.info.get(k)}
        pixels.save(buf, 'WEBP', lossless=True, exact=True, method=4, quality=90, **metadata)
        with Image.open(io.BytesIO(buf.getvalue())) as result:
            if result.size != pixels.size or result.convert('RGBA').tobytes() != pixels.tobytes():
                raise ValueError(f'lossless verification failed: {path.name}')
        return buf.getvalue()


def compact_library(source, out, all_webp=False):
    source, out = Path(source).resolve(), Path(out).resolve()
    if out.exists() or out.is_relative_to(source):
        raise ValueError('choose a new directory outside the source library')
    rows = records(source/'catalog.sqlite')
    expected = {name: digest for row in rows.values() for name, digest in image_files(row, compact=True).items()}
    inventory_rows, errors = inventory(source/'images')
    if errors or {r['path']: r['sha256'] for r in inventory_rows} != expected:
        raise ValueError('source images do not match the active catalog')
    out.parent.mkdir(parents=True, exist_ok=True)
    converted = 0
    with TemporaryDirectory(dir=out.parent) as tmp:
        stage = Path(tmp)/'library'
        shutil.copytree(source, stage, ignore=lambda folder, names: ['generations'] if Path(folder) == source/WIKI_DIR else [])
        catalog = stage/'catalog.sqlite'
        with sqlite3.connect(catalog) as db:
            for row in rows.values():
                if 'lossless_webp' in row or (not all_webp and len(row.get('paths', [row['path']])) != 1):
                    continue
                path = inside(stage/'images', row['path'])
                target = path.with_suffix('.webp')
                if all_webp and path == target:
                    if is_lossless_webp(path) and len(row.get('paths', [row['path']])) == 1:
                        continue
                    target = path.with_suffix('.lossless.webp')
                if all_webp and target.exists():
                    raise ValueError(f'destination collision: {target.name}')
                if target.exists() or (not all_webp and path.suffix.lower() != '.png'):
                    continue
                data = to_lossless_webp(path) if all_webp else compact_png(path)
                if data is None:
                    continue
                target.write_bytes(data)
                row['lossless_webp'] = {'path': target.relative_to(stage/'images').as_posix(), 'sha256': file_hash(target)}
                db.execute('UPDATE refs SET record=? WHERE id=?', (canonical(row), row['id']))
                for relative in row.get('paths', [row['path']]):
                    original = inside(stage/'images', relative)
                    if original.exists():
                        original.unlink()
                converted += 1
        if all_webp and any(p.suffix.lower() != '.webp' or not is_lossless_webp(p) for p in (stage/'images').rglob('*') if p.is_file()):
            raise ValueError('unexpected non-WebP file in output library')
        build(stage, catalog)
        result = lint(stage, catalog)
        if result['unanalysed'] or result['images']['verified'] != len(rows):
            raise ValueError('staged library failed verification')
        if out.exists():
            raise FileExistsError(out)
        os.rename(stage, out)
    return {'converted': converted, 'verified': len(rows), 'library': str(out)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=Path, default=LIBRARY)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--all-webp', action='store_true', help='also convert JPEG, transparent and metadata-bearing originals to pixel-verified display derivatives')
    args = parser.parse_args()
    print(json.dumps(compact_library(args.library, args.out, args.all_webp), ensure_ascii=False))
