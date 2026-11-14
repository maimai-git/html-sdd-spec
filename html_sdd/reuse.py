"""Extract profitable exact duplicates, without rewriting any business statements."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter

from .references import API_SECTIONS, SLOTS, expanded_spec, validate_references


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _reference(category: str, name: str) -> dict:
    return {'$ref': '#/definitions/' + category + '/' + name.replace('~', '~0').replace('/', '~1')}


def reuse_spec(spec: dict) -> dict:
    validate_references(spec)
    result = copy.deepcopy(spec)
    catalogs = copy.deepcopy(spec.get('definitions', {}))
    # Only exact duplicates of existing inline fields/rules qualify; no fuzzy matching.
    for category in ('fields', 'rules'):
        values = {}
        counts = Counter()
        for section in API_SECTIONS:
            for record in spec.get(section, []):
                for slot, kind in SLOTS.items():
                    if kind != category or not isinstance(record.get(slot), list):
                        continue
                    for value in record[slot]:
                        eligible = (isinstance(value, dict) and '$ref' not in value and 'changeStatus' not in value
                                    and isinstance(value.get('field'), str) and value['field'].strip()) if category == 'fields' else isinstance(value, str) and value.strip()
                        if eligible:
                            key = _json(value)
                            counts[key] += 1
                            values[key] = value
        replacements = {}
        for key in sorted(counts):
            count, value = counts[key], values[key]
            if count < 3:
                continue
            label = (str(value.get('where', '字段')) + '_' + value['field']) if category == 'fields' else value[:16]
            label = re.sub(r'[^\w-]+', '_', label).strip('_')[:32] or category
            digest = hashlib.sha256(key.encode()).hexdigest()
            name = label + '_' + digest[:8]
            existing = catalogs.get(category, {})
            # Never override an author's existing definition with a name collision.
            if name in existing and existing[name] != value:
                name = label + '_' + digest
                if name in existing and existing[name] != value:
                    continue
            ref = _reference(category, name)
            before_size = len(key.encode()) * count
            after_size = len(_json(ref).encode()) * count + len(_json({name: value}).encode())
            if before_size - after_size < 64:
                continue
            catalogs.setdefault(category, {})[name] = copy.deepcopy(value)
            replacements[key] = ref
        for section in API_SECTIONS:
            for record in result.get(section, []):
                for slot, kind in SLOTS.items():
                    if kind == category and isinstance(record.get(slot), list):
                        record[slot] = [copy.deepcopy(replacements.get(_json(value), value)) for value in record[slot]]
    if catalogs:
        result['definitions'] = catalogs
    # Include dictionary overhead in the final decision, and guarantee semantic equivalence.
    if len(_json(result).encode()) >= len(_json(spec).encode()):
        return copy.deepcopy(spec)
    if _json(expanded_spec(spec, drop_definitions=True)) != _json(expanded_spec(result, drop_definitions=True)):
        raise ValueError('公共定义提取改变了接口合同，本次结果未输出')
    return result


def format_spec(spec: dict) -> str:
    """One record field per line; compact nested parameter rows, without dropping values."""
    compact = lambda value: json.dumps(value, ensure_ascii=False, separators=(',', ':'))
    def record(value, indent):
        if not isinstance(value, dict):
            return ' ' * indent + compact(value)
        return ' ' * indent + '{\n' + ',\n'.join(' ' * (indent + 2) + compact(key) + ': ' + compact(item) for key, item in value.items()) + '\n' + ' ' * indent + '}'
    sections = []
    for key, value in spec.items():
        if isinstance(value, list) and value:
            body = '[\n' + ',\n'.join(record(item, 4) for item in value) + '\n  ]'
        elif key == 'definitions' and value:
            body = '{\n' + ',\n'.join('    ' + compact(category) + ': {\n' + ',\n'.join('      ' + compact(name) + ': ' + compact(item) for name, item in items.items()) + '\n    }' for category, items in value.items()) + '\n  }'
        else:
            body = compact(value)
        sections.append('  ' + compact(key) + ': ' + body)
    return '{\n' + ',\n'.join(sections) + '\n}\n'
