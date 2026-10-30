import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy import select, func, text
from sqlalchemy.orm import Session
from alembic import command
from alembic.config import Config
from app.db.models import CharacterFixedDialogue, CpuDialogue, GameSessionRecord
from app.local_runtime import create_local_runtime
from app.services.fixed_dialogue import render_text


class FixedDialogueTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name) / '자료'; self.open()
    def open(self):
        self.runtime = create_local_runtime(self.root); self.client = TestClient(self.runtime.app)
        self.headers = {'X-Local-Capability': self.runtime.capability}; self.path = '/api/local/characters/1/fixed-dialogues'
    def tearDown(self):
        self.client.close(); self.runtime.close(); self.temp.cleanup()
    def get(self): return self.client.get(self.path, headers=self.headers).json()
    def save(self, rev, edits): return self.client.patch(self.path, headers=self.headers, json={'expected_revision': rev, 'edits': edits})
    def test_values_and_restart(self):
        self.assertEqual(self.get()['slots'], {})
        with self.runtime.session_factory() as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(CharacterFixedDialogue)), 0)
        edits = {key: {'text': '' if key == 'win' else '<b>\n{{character_name}}'} for key in ('win','defeat_stage_1','defeat_stage_2','defeat_stage_3','match_first')}
        r = self.save(0, edits); self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()['slots']['win']['text'], '')
        self.assertEqual(render_text('{{character_name}} {{character_name}}', '{{character_name}}'), '{{character_name}} {{character_name}}')
        for text in ['{x}', '{{other}}', '{{character_name}', '{% test %}', '<%= name %>', '$character_name']:
            self.assertEqual(self.save(1, {'win': {'text': text}}).status_code, 422)
        for edits in [{}, {'bad': {'text': 'x'}}, {'win': {'text': None}}, {'win': {'text': '', 'extra': 1}}]:
            self.assertEqual(self.save(1, edits).status_code, 422)
        self.client.close(); self.runtime.close(); self.open()
        self.assertEqual((self.get()['revision'], self.get()['slots']['win']['text']), (1, ''))
    def test_source_and_conflicts(self):
        with self.runtime.session_factory() as session:
            rows = [CpuDialogue(cpu_character_id=1, event_key='win', text=t, active=True) for t in ('one','two')]
            session.add_all(rows); session.commit(); ids = [r.id for r in rows]
        r = self.save(0, {'win': {'legacy_dialogue_id': ids[1], 'expected_source_text': 'two'}})
        self.assertEqual(r.status_code, 200, r.text); self.assertEqual(r.json()['slots']['win']['origin']['legacy_dialogue_id'], ids[1])
        self.assertEqual(self.save(1, {'win': {'text': 'edited'}}).status_code, 200)
        self.assertEqual(self.save(2, {'win': {'legacy_dialogue_id': ids[1], 'expected_source_text': 'two'}}).json()['slots']['win']['text'], 'edited')
        self.assertEqual(self.save(3, {'win': {'legacy_dialogue_id': ids[0], 'expected_source_text': 'one'}, 'match_first': {'text': 'partial'}}).status_code, 409)
        self.assertNotIn('match_first', self.get()['slots']); self.assertEqual(self.save(2, {'win': {'text': 'stale'}}).status_code, 409)
        with self.runtime.session_factory() as session:
            session.delete(session.get(CpuDialogue, ids[1])); session.commit()
        self.assertEqual((self.get()['slots']['win']['origin']['text'], self.get()['slots']['win']['text']), ('two', 'edited'))
    def test_candidate_validation_and_direct_overwrite(self):
        with self.runtime.session_factory() as session:
            rows = [CpuDialogue(cpu_character_id=1, event_key='win', text='active', active=True),
                    CpuDialogue(cpu_character_id=1, event_key='win', text='inactive', active=False),
                    CpuDialogue(cpu_character_id=2, event_key='win', text='other cpu', active=True),
                    CpuDialogue(cpu_character_id=1, event_key='match_first', text='other event', active=True)]
            session.add_all(rows); session.commit(); ids = [r.id for r in rows]
        path = '/api/local/characters/1/fixed-dialogue-candidates'
        listing = self.client.get(path, headers=self.headers).json()['items']
        self.assertTrue(any(x['id'] == ids[1] and not x['active'] for x in listing))
        for ident, value, status in [(ids[0], 'changed', 409), (ids[1], 'inactive', 409), (ids[2], 'other cpu', 422), (ids[3], 'other event', 422), (999999, 'deleted', 409)]:
            self.assertEqual(self.save(0, {'win': {'legacy_dialogue_id': ident, 'expected_source_text': value}}).status_code, status)
        self.assertEqual(self.get()['slots'], {})
        self.assertEqual(self.save(0, {'win': {'text': ''}}).status_code, 200)
        self.assertEqual(self.save(1, {'win': {'legacy_dialogue_id': ids[0], 'expected_source_text': 'active'}}).status_code, 409)
        self.assertEqual(self.get()['slots']['win']['text'], '')

    def test_two_writers(self):
        def run(value): return self.save(0, {'win': {'text': value}}).status_code
        with ThreadPoolExecutor(max_workers=2) as executor: self.assertEqual(sorted(executor.map(run, ['first','second'])), [200,409])

    def test_equal_legacy_text_is_independently_selected_for_each_cpu(self):
        with self.runtime.session_factory() as session:
            rows = [CpuDialogue(cpu_character_id=cpu, event_key='win', text='same', active=True) for cpu in (1, 2)]
            session.add_all(rows); session.commit(); ids = [row.id for row in rows]
        for cpu, ident in zip((1, 2), ids):
            response = self.client.patch(f'/api/local/characters/{cpu}/fixed-dialogues', headers=self.headers, json={
                'expected_revision': 0, 'edits': {'win': {'legacy_dialogue_id': ident, 'expected_source_text': 'same'}}})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.json()['slots']['win']['origin']['legacy_dialogue_id'], ident)
        with self.runtime.session_factory() as session:
            row = session.get(CpuDialogue, ids[0]); row.text = 'changed'; session.commit()
        self.assertEqual(self.get()['slots']['win']['origin']['text'], 'same')
        other = self.client.get('/api/local/characters/2/fixed-dialogues', headers=self.headers).json()
        self.assertEqual(other['slots']['win']['origin']['legacy_dialogue_id'], ids[1])
    def test_commit_failure(self):
        with patch.object(Session, 'commit', side_effect=RuntimeError('commit failed')):
            with self.assertRaises(RuntimeError): self.save(0, {'win': {'text': 'not committed'}})
        self.assertEqual(self.get()['slots'], {})

    def test_upgrade_existing_database_preserves_rows_and_is_repeatable(self):
        content = self.client.patch('/api/local/characters/1/content', headers=self.headers, json={
            'expected_revision': 0, 'prompts': {'appearance': {'positive': 'preserved'}}})
        self.assertEqual(content.status_code, 200, content.text)
        with self.runtime.session_factory.begin() as session:
            session.add(GameSessionRecord(id='fixed-migration-fixture', user_id=self.runtime.member_id,
                match_seed=1, cpu_choices=[], players=[], human_action_indices=[], status='completed',
                presentation={'dialogue': 'completed-before-upgrade'}))
        backend = Path(__file__).resolve().parents[1]
        cfg = Config(str(backend / 'alembic.ini'))
        cfg.set_main_option('script_location', str(backend / 'alembic'))
        tables = ('cpu_characters', 'cpu_dialogues', 'game_sessions', 'character_content', 'character_voice_links', 'local_media_assets')
        with self.runtime.engine.connect() as connection:
            cfg.attributes['connection'] = connection
            command.downgrade(cfg, '20261021_0013')
            before = {table: connection.execute(text(f'SELECT * FROM {table}')).all() for table in tables}
            command.upgrade(cfg, 'head')
            command.upgrade(cfg, 'head')
            after = {table: connection.execute(text(f'SELECT * FROM {table}')).all() for table in tables}
            self.assertEqual(before, after)
            self.assertEqual(connection.execute(text('SELECT count(*) FROM character_fixed_dialogues')).scalar_one(), 0)
