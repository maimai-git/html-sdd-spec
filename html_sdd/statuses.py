"""Single source of status labels, section subsets and semantic colors."""
from __future__ import annotations
import copy
import json
from functools import lru_cache
from pathlib import Path

@lru_cache(maxsize=1)
def _registry():
    return json.loads((Path(__file__).parent/'assets/statuses.json').read_text(encoding='utf-8'))

def registry():
    return copy.deepcopy(_registry())

def status_info(value, section):
    data=_registry(); allowed=data['sections'].get(section, [])
    valid=isinstance(value,str) and value in allowed
    label=value if valid else '待核实'
    return {'label':label,'tone':data['statuses'][label], 'note':'' if valid else (value if isinstance(value,str) else '')}

def status_records(spec):
    if isinstance(spec.get('metadata'),dict):yield 'metadata','metadata',spec['metadata']
    for section in _registry()['sections']:
        if section in {'metadata','developmentStatus','acceptance'}:continue
        values=spec.get(section,[])
        if isinstance(values,list):
            for i,record in enumerate(values):
                if isinstance(record,dict):
                    yield section,f'{section}[{i}]',record
                    if section=='requirements' and isinstance(record.get('acceptance'),list):
                        for j,item in enumerate(record['acceptance']):
                            if isinstance(item,dict):yield 'acceptance',f'{section}[{i}].acceptance[{j}]',item

def status_issues(spec):
    metadata=spec.get('metadata',{})
    policy=metadata.get('statusPolicy','legacy') if isinstance(metadata,dict) else 'legacy'
    if policy not in ('legacy','strict'):
        yield 'error','STATUS_POLICY_INVALID','metadata.statusPolicy','只能为 strict 或 legacy'
    for section,path,record in status_records(spec):
        if section in {'apis','tables'} and 'developmentStatus' in record:
            value=record['developmentStatus']
            if not isinstance(value,str) or value not in _registry()['sections']['developmentStatus']:
                yield 'error','DEVELOPMENT_STATUS_INVALID',path+'.developmentStatus','开发状态必须来自统一枚举'

        if 'statusNote' in record and not isinstance(record['statusNote'],str):
            yield 'error','STATUS_NOTE_INVALID',path+'.statusNote','状态说明必须为字符串'
        if section=='agents' and 'status' not in record:continue
        value=record.get('status')
        if not isinstance(value,str) or value not in _registry()['sections'][section]:
            strict=policy=='strict' or section=='plans'
            bad_type='status' in record and not isinstance(value,str)
            yield ('error' if strict or bad_type else 'warning'),('STATUS_INVALID' if strict or bad_type else 'LEGACY_STATUS_TEXT'),path+'.status','状态须来自对应板块枚举；旧说明保留为 statusNote，缺省显示待核实'

def normalize_statuses(spec):
    result=copy.deepcopy(spec)
    for section,path,record in status_records(result):
        value=record.get('status')
        if isinstance(value,str) and value in _registry()['sections'][section]:continue
        if section=='plans':raise ValueError(path+'：排期状态必须人工确认，不能自动推断')
        if 'statusNote' in record and not isinstance(record['statusNote'],str):raise ValueError(path+'：statusNote 必须为字符串')
        if value is not None and not isinstance(value,str):raise ValueError(path+'：状态类型错误')
        if value:
            record['statusNote']='\n'.join(x for x in (record.get('statusNote',''),value) if x)
        record['status']='待核实'
    result['metadata']['statusPolicy']='strict'
    return result

def status_css():
    return '\n'.join('.status.'+tone+'{color:'+colors['color']+';background:'+colors['background']+'}.catalog-status.'+tone+'{color:'+colors['color']+'}' for tone,colors in _registry()['tones'].items())
