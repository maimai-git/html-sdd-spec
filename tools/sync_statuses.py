"""Generate schema constraints and the status reference from the single registry."""
import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from html_sdd.statuses import registry

def artifacts():
    data=registry();path=ROOT/'schema/html-sdd.schema.json';schema=json.loads(path.read_text())
    meta=schema['properties']['metadata']['properties'];meta['statusPolicy']={'type':'string','enum':['strict','legacy']};meta['statusNote']={'type':'string'}
    schema['$defs']['record']['properties']['statusNote']={'type':'string'}
    schema['$defs']['acceptance']['allOf'][1]['properties']['statusNote']={'type':'string'}
    for category in ('api','table'):
        schema['$defs'][category]['allOf'][1]['properties']['developmentStatus']['enum']=data['sections']['developmentStatus']
    schema['$defs']['plan']['allOf'][1]['properties']['status']['enum']=data['sections']['plans']
    props={'metadata':{'properties':{'status':{'enum':data['sections']['metadata']}}}}
    for section,labels in data['sections'].items():
        if section in ('metadata','developmentStatus','acceptance'):continue
        props[section]={'type':'array','items':{'type':'object','required':['status'],'properties':{'status':{'type':'string','enum':labels},'statusNote':{'type':'string'}}}}
    props['agents']['items'].pop('required',None)
    props['requirements']['items']['properties']['acceptance']={'type':'array','items':{'type':'object','required':['status'],'properties':{'status':{'enum':data['sections']['acceptance']},'statusNote':{'type':'string'}}}}
    schema['allOf']=[{'if':{'properties':{'metadata':{'required':['statusPolicy'],'properties':{'statusPolicy':{'const':'strict'}}}}},'then':{'properties':props}}]
    lines=['# 状态规范','', '由 `html_sdd/assets/statuses.json` 生成，请勿手改；修改字典后运行 `python3 tools/sync_statuses.py`。', '', '| 语义色 | 文字色 | 背景色 |','|---|---|---|']
    for tone,colors in data['tones'].items():lines.append(f"| {tone} | `{colors['color']}` | `{colors['background']}` |")
    lines+=['','| 板块 | 允许的状态 |','|---|---|']
    for section,labels in data['sections'].items():lines.append('| '+section+' | '+'、'.join(labels)+' |')
    lines+=['','`status` 保存短枚举，`statusNote` 保存说明。新文档启用 `metadata.statusPolicy=strict`；旧文档默认 legacy，未知长句警告并显示灰色“待核实”，不从关键词猜状态。排期与开发状态始终严格；开发状态不代表部署或验收。']
    return {path:json.dumps(schema,ensure_ascii=False,indent=2)+'\n',ROOT/'docs/状态规范.md':'\n'.join(lines)+'\n'}
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check',action='store_true');args=parser.parse_args()
    bad=[]
    for path,text in artifacts().items():
        if args.check:
            if not path.exists() or path.read_text()!=text:bad.append(str(path.relative_to(ROOT)))
        else:path.write_text(text)
    if bad:print('状态副本未同步：'+','.join(bad));sys.exit(1)
    print('状态规范和schema已同步')
