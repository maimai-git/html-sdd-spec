"""Local, single-hop definitions for API fields, rules, and notes; examples stay opaque."""
from __future__ import annotations

import copy
import re
from typing import Any

API_SECTIONS = ('apis', 'existingInterfaces')
SLOTS = {'request': 'fields', 'response': 'fields', 'rules': 'rules', 'notes': 'rules'}
FIELD_CHANGE_STATUSES = ('新增', '修改', '删除')


class DefinitionError(ValueError):
    def __init__(self, path: str, message: str):
        self.path = path
        super().__init__(f'{path}: {message}')


def _values(value: Any, category: str, path: str) -> list:
    items = value if isinstance(value, list) else [value]
    if not items:
        raise DefinitionError(path, '公共定义不能是空数组')
    for item in items:
        valid = (isinstance(item, dict) and '$ref' not in item
                 and 'changeStatus' not in item and isinstance(item.get('field'), str) and bool(item['field'].strip())) if category == 'fields' else isinstance(item, str) and bool(item.strip())
        if not valid:
            raise DefinitionError(path, 'fields 必须为具名字段对象，rules 必须为非空字符串；定义内不能互相引用')
    return items


def definitions(spec: dict) -> dict:
    result = spec.get('definitions', {})
    if not isinstance(result, dict) or set(result) - {'fields', 'rules'}:
        raise DefinitionError('definitions', '只支持 fields、rules 本地字典')
    for category, values in result.items():
        if not isinstance(values, dict):
            raise DefinitionError('definitions.' + category, '必须为字典')
        for name, value in values.items():
            if not isinstance(name, str) or not name:
                raise DefinitionError('definitions.' + category, '定义名称不能为空')
            _values(value, category, 'definitions.' + category + '.' + name)
    return result


def _resolve(ref: dict, category: str, defs: dict, path: str) -> list:
    allowed = {'$ref', 'changeStatus'} if category == 'fields' else {'$ref'}
    if set(ref) - allowed:
        raise DefinitionError(path, '引用对象只能包含 $ref，不允许隐式覆盖')
    pointer = ref['$ref']
    prefix = '#/definitions/' + category + '/'
    if not isinstance(pointer, str) or not pointer.startswith(prefix):
        raise DefinitionError(path, '只支持 ' + prefix + '名称 的本地引用')
    name = pointer[len(prefix):]
    if not name or '/' in name or re.search(r'~(?![01])', name):
        raise DefinitionError(path, '名称须使用 JSON Pointer 的 ~0、~1 转义')
    name = name.replace('~1', '/').replace('~0', '~')
    if name not in defs.get(category, {}):
        raise DefinitionError(path, '公共定义不存在：' + pointer)
    rows = copy.deepcopy(_values(defs[category][name], category, path))
    if 'changeStatus' in ref:
        for row in rows:
            row['changeStatus'] = ref['changeStatus']
    return rows


def expand_api(spec: dict, record: dict, path: str = 'api', *, _defs=None) -> dict:
    defs = definitions(spec) if _defs is None else _defs
    result = copy.deepcopy(record)
    for slot, category in SLOTS.items():
        if slot not in result or (slot == "notes" and isinstance(result[slot], str)):
            continue
        if not isinstance(result[slot], list):
            raise DefinitionError(path + '.' + slot, '参数、规则和说明的引用必须放在数组中')
        rows = []
        for index, item in enumerate(result[slot]):
            if isinstance(item, dict) and '$ref' in item:
                rows.extend(_resolve(item, category, defs, f'{path}.{slot}[{index}]'))
            else:
                if not isinstance(item, dict if category == 'fields' else str):
                    raise DefinitionError(f'{path}.{slot}[{index}]', '字段必须为对象，规则和说明必须为字符串或纯引用')
                rows.append(item)
        result[slot] = rows
    return result


def field_change_errors(spec: dict):
    for section, slots in (('apis', ('request', 'response')),
                           ('existingInterfaces', ('request', 'response')),
                           ('tables', ('columns',))):
        records = spec.get(section, [])
        if not isinstance(records, list):
            continue
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                continue
            for slot in slots:
                items = record.get(slot)
                if not isinstance(items, list):
                    continue
                for row_index, row in enumerate(items):
                    if isinstance(row, dict) and 'changeStatus' in row and row['changeStatus'] not in FIELD_CHANGE_STATUSES:
                        yield f'{section}[{index}].{slot}[{row_index}].changeStatus'


def validate_references(spec: dict) -> None:
    defs = definitions(spec)
    for section in API_SECTIONS:
        records = spec.get(section, [])
        if not isinstance(records, list):
            raise DefinitionError(section, '接口分类必须为数组')
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                raise DefinitionError(f'{section}[{index}]', '接口记录必须为对象')
            expand_api(spec, record, f'{section}[{index}]', _defs=defs)


def expanded_spec(spec: dict, *, drop_definitions: bool = False) -> dict:
    validate_references(spec)
    defs = definitions(spec)
    result = copy.deepcopy(spec)
    for section in API_SECTIONS:
        if isinstance(spec.get(section), list):
            result[section] = [expand_api(spec, record, f'{section}[{index}]', _defs=defs)
                               if isinstance(record, dict) else copy.deepcopy(record)
                               for index, record in enumerate(spec[section])]
    if drop_definitions:
        result.pop('definitions', None)
    return result
