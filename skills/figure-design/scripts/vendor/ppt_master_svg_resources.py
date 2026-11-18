"""Local SVG resource-closure checks extracted from PPT Master.

Copyright (c) 2025-2026 Hugo He. MIT; see third_party/ppt-master/LICENSE.
Only resource-closure constants/functions are retained; no runtime upstream lookup.
"""
from __future__ import annotations
import base64
import binascii
import re
from urllib.parse import unquote_to_bytes
from xml.etree import ElementTree as ET

_SVG_NAMESPACE = 'http://www.w3.org/2000/svg'


_SVG_URL_REFERENCE_RE = re.compile(r'url\(\s*([^)]+?)\s*\)', re.IGNORECASE)


_SVG_CSS_URL_ATTRIBUTES = frozenset({
    'background',
    'background-image',
    'clip-path',
    'color-profile',
    'cursor',
    'fill',
    'filter',
    'marker',
    'marker-end',
    'marker-mid',
    'marker-start',
    'mask',
    'stroke',
    'style',
})


_SVG_DIRECT_RESOURCE_ATTRIBUTES = frozenset({'poster', 'src'})


_SVG_DATA_URI_DEPTH_LIMIT = 8


_SVG_EXTERNAL_DOCTYPE_RE = re.compile(
    br'<!DOCTYPE\b[^>]*\b(?:PUBLIC|SYSTEM)\b',
    re.IGNORECASE | re.DOTALL,
)


_XML_STYLESHEET_HREF_RE = re.compile(
    r'\bhref\s*=\s*([\'"])(.*?)\1',
    re.IGNORECASE | re.DOTALL,
)


def _decode_svg_data_uri(raw: str) -> tuple[bytes | None, str | None]:
    """Decode an SVG data URI; return ``(None, None)`` for other media."""
    value = raw.strip().strip('\'"')
    if not value.lower().startswith('data:'):
        return None, None
    header, separator, payload = value.partition(',')
    media_type = header[5:].split(';', 1)[0].strip().lower()
    if media_type != 'image/svg+xml':
        return None, None
    if not separator:
        return None, 'invalid embedded SVG data URI'
    is_base64 = any(
        token.strip().lower() == 'base64'
        for token in header.split(';')[1:]
    )
    try:
        decoded = (
            base64.b64decode(payload, validate=True)
            if is_base64
            else unquote_to_bytes(payload)
        )
    except (ValueError, binascii.Error):
        return None, 'invalid embedded SVG data URI'
    return decoded, None


def _svg_reference_error(raw: str, depth: int) -> str | None:
    """Return an external or recursively embedded SVG resource error."""
    value = raw.strip().strip('\'"')
    if not value:
        return 'empty resource reference'
    if value.startswith('#'):
        return None
    if not value.lower().startswith('data:'):
        return f'unpackaged external resource {value!r}'

    nested_svg, decode_error = _decode_svg_data_uri(value)
    if decode_error is not None:
        return decode_error
    if nested_svg is None:
        return None
    if depth >= _SVG_DATA_URI_DEPTH_LIMIT:
        return 'embedded SVG resource nesting exceeds the safety limit'
    nested_error = _svg_image_payload_error(nested_svg, depth + 1)
    if nested_error is None:
        return None
    return f'embedded SVG resource is not closed: {nested_error}'


def _xml_stylesheet_error(raw_bytes: bytes, depth: int) -> str | None:
    """Return an external XML stylesheet processing-instruction error."""
    parser = ET.XMLPullParser(events=('pi',))
    try:
        parser.feed(raw_bytes)
        parser.close()
    except ET.ParseError:
        return None
    for _event, instruction in parser.read_events():
        text = (instruction.text or '').strip()
        if not text.lower().startswith('xml-stylesheet'):
            continue
        match = _XML_STYLESHEET_HREF_RE.search(text)
        if match is None:
            return 'XML stylesheet processing instruction lacks href'
        reference_error = _svg_reference_error(match.group(2), depth)
        if reference_error is not None:
            return f'XML stylesheet is not closed: {reference_error}'
    return None


def _svg_image_payload_error(raw_bytes: bytes, depth: int) -> str | None:
    """Return why one SVG image payload is not a closed packaged resource."""
    if _SVG_EXTERNAL_DOCTYPE_RE.search(raw_bytes):
        return 'unpackaged external XML doctype'
    try:
        root = ET.fromstring(raw_bytes)
    except ET.ParseError as exc:
        return f'invalid SVG XML: {exc}'
    if root.tag != f'{{{_SVG_NAMESPACE}}}svg':
        return 'root must use the SVG namespace'

    stylesheet_error = _xml_stylesheet_error(raw_bytes, depth)
    if stylesheet_error is not None:
        return stylesheet_error
    for elem in root.iter():
        tag = str(elem.tag).rsplit('}', 1)[-1]
        for raw_name, raw_value in elem.attrib.items():
            name = raw_name.rsplit('}', 1)[-1]
            if name == 'href' and tag != 'a':
                reference_error = _svg_reference_error(raw_value, depth)
                if reference_error is not None:
                    return reference_error
            elif name in _SVG_DIRECT_RESOURCE_ATTRIBUTES:
                reference_error = _svg_reference_error(raw_value, depth)
                if reference_error is not None:
                    return reference_error
            elif name == 'data' and tag == 'object':
                reference_error = _svg_reference_error(raw_value, depth)
                if reference_error is not None:
                    return reference_error
            elif name == 'srcset' and raw_value.strip():
                return 'srcset resource lists are not closed SVG resources'

            if name not in _SVG_CSS_URL_ATTRIBUTES:
                continue
            for match in _SVG_URL_REFERENCE_RE.finditer(raw_value):
                reference_error = _svg_reference_error(match.group(1), depth)
                if reference_error is not None:
                    return f'url() resource is not closed: {reference_error}'

        if tag != 'style':
            continue
        style_text = ''.join(elem.itertext())
        if re.search(r'@import\b', style_text, flags=re.IGNORECASE):
            return 'unpackaged CSS import'
        for match in _SVG_URL_REFERENCE_RE.finditer(style_text):
            reference_error = _svg_reference_error(match.group(1), depth)
            if reference_error is not None:
                return f'url() resource is not closed: {reference_error}'
    return None


def svg_image_payload_error(raw_bytes: bytes) -> str | None:
    """Return why a nested SVG image is not a closed packaged resource."""
    return _svg_image_payload_error(raw_bytes, 0)

