#!/usr/bin/env python3
"""Run three isolated scripted user journeys; synthetic evidence, never a GUI claim."""
from pathlib import Path
import argparse
import io
import json
import subprocess
import sys
import tempfile
import zipfile
import install

REPO=Path(__file__).resolve().parents[1]


def command(script,root,*args):
    p=subprocess.run([sys.executable,str(script),'--root',str(root),*args],capture_output=True,text=True,encoding='utf-8')
    if p.returncode: raise RuntimeError(p.stderr)
    return json.loads(p.stdout)['result']


def journey(base,name,legacy=False,existing=False):
    root=base/name;root.mkdir()
    def put(path,text):
        target=root/path;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(text,encoding='utf-8');return path
    preserved={}
    if existing:
        put('用户已有笔记.md','用户已有知识库笔记，必须保留原文件')
        preserved['用户已有笔记.md']=(root/'用户已有笔记.md').read_bytes()
    if legacy:
        oldrepo=base/'historical-v0.1.1';oldrepo.mkdir()
        archive=subprocess.run(['git','-c','core.autocrlf=false','archive','--format=zip','v0.1.1'],cwd=REPO,capture_output=True,check=True).stdout
        with zipfile.ZipFile(io.BytesIO(archive)) as z:z.extractall(oldrepo)
        p=subprocess.run([sys.executable,str(oldrepo/'tools/install.py'),'--workspace',str(root),'--init'],capture_output=True,text=True,encoding='utf-8')
        if p.returncode: raise RuntimeError(p.stderr)
        script=oldrepo/'skills/chao-knowledge/scripts/kb.py'
        put('00-待整理/old.md','历史会议记录原文，升级后继续可用')
        m=command(script,root,'ingest','--title','历史会议资料','--file','00-待整理/old.md')['material']
        old=command(script,root,'remember','--key','历史偏好','--text','提供具体例子','--scope','task=总结')['rule']
        command(script,root,'confirm','--id',old['id'],'--quote','确认用于总结')
        put('00-待整理/draft.md','历史会议总结作品')
        o=command(script,root,'save','--title','历史作品','--file','00-待整理/draft.md','--source',m['id'])['output']
        for path in [m['original'],m['text_path'],o['path']]:preserved[path]=(root/path).read_bytes()
    installed=install.install(str(root),initialize=True,update=legacy)
    script=root/'.codebuddy/skills/chao-knowledge/scripts/kb.py'
    for field,value in [('身份','办公效率内容创作者（虚构验收设定）'),('受众','AI初学者'),('当前目标','完成一条会议记录口播'),('能力边界','没有外部作者的企业服务经历')]:
        command(script,root,'profile','--field',field,'--value',value,'--quote','本测试用户设定：'+value)
    put('00-收件箱/source.md','外部合成资料：虚构作者服务过十二家企业。整理会议笔记要分决策、待办和待确认，写清负责人和时间。')
    m=command(script,root,'ingest','--title','会议记录方法','--file','00-收件箱/source.md','--collection','对标内容','--provenance','external','--author','虚构作者','--project','会议项目')['material']
    assert command(script,root,'search','--query','会议记录')['results']
    source=m['id']
    put('00-收件箱/topic.md','选题：会议后如何找到下一步')
    topic=command(script,root,'save','--title','会议记录选题','--file','00-收件箱/topic.md','--stage','选题池','--source',source,'--project','会议项目')['output']
    put('00-收件箱/draft.md','合成验收稿：会议开完，先把决策、待办和待确认分开。每条待办写清负责人和时间。')
    draft=command(script,root,'save','--title','会议口播初稿','--file','00-收件箱/draft.md','--parent',topic['id'],'--stage','草稿','--duration','60','--scope','task=口播')['output']
    put('00-收件箱/revised.md','合成验收二稿：开完会，下一步是什么？先分清决定、待办、待确认。写上负责人和时间，没有时间就标待确认。')
    revised=command(script,root,'save','--title','会议口播二稿','--file','00-收件箱/revised.md','--parent',draft['id'],'--stage','待确认','--change-note','只修改本次开头')['output']
    rule=command(script,root,'remember','--key','入门口播风格','--text','少用术语，句子短一点','--scope','task=口播','--scope','audience=AI初学者','--scope','platform=抖音')['rule']
    assert rule['status']=='proposed'
    command(script,root,'confirm','--id',rule['id'],'--quote','测试用户确认只在这个范围保存')
    # New processes exercise disk reload; this intentionally makes no host-GUI claim.
    ctx=command(script,root,'context','--task','继续会议记录口播','--scope','task=口播','--scope','audience=AI初学者','--scope','platform=抖音')
    assert rule['id'] in [r['id'] for r in ctx['rules']]
    other=command(script,root,'context','--task','专业技术方案','--scope','task=方案','--scope','audience=工程师')
    assert rule['id'] not in [r['id'] for r in other['rules']]
    done=command(script,root,'approve','--id',revised['id'],'--quote','测试设定：核对完成')['output']
    pub=command(script,root,'publish','--id',done['id'],'--platform','抖音','--audience','AI初学者','--at','2026-10-06T12:00:00+08:00','--quote','测试设定：已发布；没有执行真实发布')['output']
    put('00-收件箱/metrics.json',json.dumps({'observed_at':'2026-10-06T20:00:00+08:00','window_hours':24,'views':1000,'likes':30,'comments':4,'saves':None,'note':'合成验收数据，不是真实平台数据'},ensure_ascii=False))
    f=command(script,root,'feedback','--id',pub['id'],'--file','00-收件箱/metrics.json')
    command(script,root,'experience','--kind','observation','--title','一次观察','--text','合成反馈中的点赞率为 3%，不能证明写法导致了结果','--feedback',f['id'],'--scope','platform=抖音')
    health=command(script,root,'health'); saved=command(script,root,'health','--save')
    assert health['summary']['P0']==health['summary']['P1']==0,health
    assert saved['summary']==health['summary']
    for path,data in preserved.items(): assert (root/path).read_bytes()==data,path
    snapshot=(root/'.chao/state.json').read_bytes();command(script,root,'init');assert snapshot==(root/'.chao/state.json').read_bytes()
    return {'journey':name,'status':'PASS','install':installed['status'],'health':health['summary'],'preserved_files':len(preserved),'cross_session':'independent script processes; not GUI','tree':sorted(p.relative_to(root).as_posix() for p in root.rglob('*') if not any(part in {'.codebuddy','.chao'} for part in p.relative_to(root).parts))}


def run(base):
    return {'evidence':'synthetic script journeys','version':'0.3.3','journeys':[journey(base,'A-new-user'),journey(base,'B-existing-materials',existing=True),journey(base,'C-upgrade-v0.1.1',legacy=True)]}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--directory',help='Optional empty directory to retain the three test knowledge bases')
    a=p.parse_args()
    if a.directory:
        base=Path(a.directory).absolute()
        if base.exists() and any(base.iterdir()):raise ValueError('Acceptance directory must be empty')
        base.mkdir(parents=True,exist_ok=True)
        result=run(base.resolve());(base/'acceptance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    else:
        with tempfile.TemporaryDirectory(prefix='chao-acceptance-') as tmp:result=run(Path(tmp).resolve())
    print(json.dumps({k:v for k,v in result.items() if k!='journeys'},ensure_ascii=False))
    for row in result['journeys']:print(json.dumps({k:v for k,v in row.items() if k!='tree'},ensure_ascii=False))


if __name__=='__main__':main()
