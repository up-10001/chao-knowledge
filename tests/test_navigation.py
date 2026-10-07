"""User-facing navigation projection regressions, preserving facts and manual edits."""
import json
import re
from test_kb import WorkspaceCase, kb

class NavigationTests(WorkspaceCase):
    def setUp(self):
        super().setUp(); self.init()

    def text(self):
        return (self.root/'知识库地图.md').read_text(encoding='utf-8')

    def test_empty_navigation_has_all_entry_points_and_honest_zero_counts(self):
        text=self.text()
        for phrase in ['# 我的知识库导航','个人档案：已填写 0 项','资料：0 份','作品：0 份','长期要求：0 条','反馈：0 份','项目：0 个',
                       '选题池 → 草稿 → 待确认 → 已完成 → 已发布与复盘','暂时没有项目，后续创建项目时会自动出现在这里。','当前有效长期要求：0 条','待确认规则：0 条','已验证经验：0 条','最近一次健康检查：尚未保存结果']:
            self.assertIn(phrase,text)
        for path in ['00-收件箱/','02-资料库/对标内容/','02-资料库/用户反馈/','02-资料库/行业资料/','02-资料库/素材/','01-我的档案/我的表达风格.md']:
            self.assertIn(']('+path+')',text)
        self.assertNotIn('.chao/state.json',text)
        self.assertNotIn('最近反馈',text)

    def test_profile_counts_and_badges_update_without_repeating_private_text(self):
        value='这段完整背景只保留在档案，不应出现在导航'
        for field in ['身份','受众','业务']:
            self.call('profile','--field',field,'--value',value,'--quote',value)
        text=self.text();self.assertIn('个人档案：已填写 3 项',text);self.assertNotIn(value,text)
        self.assertIn('[我是谁](01-我的档案/我是谁.md) | 已填写',text)
        self.assertIn('[我的经历](01-我的档案/我的经历.md) | 待补充',text)
        self.call('profile-forget','--field','业务','--quote','删除合成业务字段')
        self.assertIn('个人档案：已填写 2 项',self.text())

    def test_recent_material_shows_category_provenance_reading_and_real_path(self):
        self.put('00-收件箱/material.txt','合成外部资料')
        row=self.call('ingest','--title','示例 | [资料]','--file','00-收件箱/material.txt','--collection','行业资料','--provenance','external')['material']
        text=self.text();self.assertIn('资料：1 份',text)
        for value in ['示例 \\| \\[资料\\]','行业资料','外部资料','正文可读',']('+row['text_path']+')']:
            self.assertIn(value,text)
        self.assertNotIn('`'+row['id']+'`',text)
        self.call('ingest','--title','只有网页链接','--url','https://example.com/note')
        self.assertIn('只有链接',self.text())

    def test_saved_versions_show_flow_stages_heads_and_project_entries(self):
        original=self.output();self.put('00-收件箱/draft.md','合成二稿')
        newer=self.call('save','--title','二稿','--file','00-收件箱/draft.md','--parent',original['id'],'--stage','待确认','--project','会议项目')['output']
        text=self.text()
        self.assertIn('作品：2 份',text);self.assertIn('历史版本',text);self.assertIn('当前分支末版',text);self.assertIn('| 二稿 | 待确认 |',text)
        for row in [original,newer]:self.assertIn(']('+row['path']+')',text)
        self.assertIn('项目：1 个',text)
        link=re.search(r'\[会议项目\]\((04-项目/[^)]+)\)',text).group(1)
        self.assertTrue((self.root/link).is_file())
        self.assertNotIn('暂时没有项目',text)

    def test_rule_feedback_and_verified_experience_counts_follow_actual_records(self):
        pending=self.proposal();self.assertIn('待确认规则：1 条',self.text());self.activate(pending)
        self.assertIn('当前有效长期要求：1 条',self.text());self.assertIn('待确认规则：0 条',self.text())
        feedback=[]
        for title in ['独立合成作品甲','独立合成作品乙']:
            self.put('00-收件箱/draft.md','合成稿，用户核验仅用于测试')
            output=self.call('save','--title',title,'--file','00-收件箱/draft.md','--scope','task=口播','--duration','60')['output']
            approved=self.call('approve','--id',output['id'],'--quote','合成测试核对完成')['output']
            published=self.call('publish','--id',approved['id'],'--platform','抖音','--audience','AI初学者','--at','2026-10-06T12:00:00+08:00','--quote','合成发布登记，不是真实上传')['output']
            feedback.append(self.call('feedback','--id',published['id'],'--file',self.metrics())['id'])
        args=['experience','--kind','validated','--title','合成已验证经验','--text','仅用于测试统计','--scope','task=口播','--quote','确认合成证据口径一致']
        for fid in feedback:args+=['--feedback',fid]
        self.call(*args)
        self.assertIn('反馈：2 份',self.text());self.assertIn('已验证经验：1 条',self.text())
        self.assertIn('## 最近反馈',self.text())
        self.assertNotRegex(self.text(),r'`[mofre]-[a-f0-9]{12}`')
        self.call('revoke','--id',pending['id'],'--quote','撤销合成规则')
        self.assertIn('当前有效长期要求：0 条',self.text())

    def test_material_project_creates_entry_without_inventing_project_records(self):
        self.put();self.call('ingest','--title','项目资料','--file','00-收件箱/source.md','--project','资料项目')
        text=self.text();self.assertIn('项目：1 个',text)
        link=re.search(r'\[资料项目\]\((04-项目/[^)]+)\)',text).group(1)
        self.assertTrue((self.root/link).is_file());self.assertNotIn('projects',kb.load(self.root))

    def test_saved_health_updates_summary_only_and_default_health_stays_readonly(self):
        state_before=kb.load(self.root);map_before=self.text();self.call('health')
        self.assertEqual(self.text(),map_before);self.assertEqual(kb.load(self.root),state_before)
        result=self.call('health','--save');state_after=kb.load(self.root)
        for key in set(state_before)-{'views','updated_at'}:self.assertEqual(state_after[key],state_before[key])
        self.assertEqual(set(state_after),set(state_before))
        self.assertIn('最近一次已保存健康检查',self.text());self.assertIn('需要核对',self.text())
        self.assertIn('检查时间：'+result['checked_at'],self.text())
        self.assertEqual(self.call('sync')['changed'],[])
        report=(self.root/'.chao/latest-health.json').read_bytes()
        self.call('profile','--field','身份','--value','合成用户','--quote','合成用户')
        self.assertEqual((self.root/'.chao/latest-health.json').read_bytes(),report)
        self.assertIn('最近一次已保存健康检查',self.text())

    def test_hand_edited_map_is_retained_for_writes_and_saved_health(self):
        path=self.root/'知识库地图.md';manual='用户的手工地图，禁止覆盖';path.write_text(manual,encoding='utf-8')
        before=(self.root/'.chao/state.json').read_bytes()
        with self.assertRaisesRegex(kb.KBError,'手工改动'):
            self.call('profile','--field','身份','--value','不能写','--quote','不能写')
        self.call('health','--save')
        self.assertEqual(path.read_text(encoding='utf-8'),manual);self.assertEqual((self.root/'.chao/state.json').read_bytes(),before)
        self.assertIn('知识库地图.md',self.call('sync')['changed'])

    def test_recent_tables_are_bounded_and_generated_from_complete_state(self):
        for n in range(10):
            self.put('00-收件箱/source.md','不同资料内容 '+str(n))
            self.call('ingest','--title','合成资料'+str(n),'--file','00-收件箱/source.md')
        text=self.text();self.assertIn('资料：10 份',text)
        section=text.split('## 最近资料')[1].split('## 最近作品')[0]
        self.assertEqual(section.count('打开正文'),8)
        self.assertEqual(len(kb.load(self.root)['materials']),10)

    def test_saved_health_journal_recovery_accepts_only_managed_report_paths(self):
        path=self.root/'.chao/latest-health.json';data=b'{"status":"attention"}'
        path.write_bytes(data)
        journal={'format':1,'files':[{'path':'.chao/latest-health.json','before':None,'after':kb.digest(data),'data':None}]}
        (self.root/'.chao/pending-write.json').write_text(json.dumps(journal),encoding='utf-8')
        self.assertEqual(self.call('recover')['status'],'plan')
        self.call('recover','--apply','--quote','确认恢复合成测试中断的健康报告')
        self.assertFalse(path.exists())
        self.assertTrue(list((self.root/'.chao/recovery-retained').rglob('latest-health.json')))
