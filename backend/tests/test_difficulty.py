from dataclasses import asdict, replace
import copy
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models import GameSessionRecord, GameSetting, User, LocalPlayState
from app.local_runtime import create_local_runtime
from app.services.difficulty import KEY, DifficultyError, resolve, validate_snapshot
from app.services.game_setup import CpuChoice, create_production_cpu_agent
from app.services.game_registry import GameRegistry
from app.db.models import GameResultDelivery, GameResultDeliveryEntry
from app.services.result_delivery import acknowledge_result


def _ack_all_results(db, session_id):
    record = db.get(GameSessionRecord, session_id)
    delivery = db.get(GameResultDelivery, session_id)
    if delivery is None:
        return
    entries = db.scalars(select(GameResultDeliveryEntry).where(
        GameResultDeliveryEntry.session_id == session_id
    ).order_by(GameResultDeliveryEntry.ordinal)).all()
    while delivery.acked_ordinal < len(entries):
        entry = entries[delivery.acked_ordinal]
        acknowledge_result(db, record, generation=delivery.generation, event_id=entry.event_id,
                           ordinal=entry.ordinal, expected_revision=delivery.revision)


class DifficultyTests(unittest.TestCase):
    def test_resolver_full_table_and_strict_snapshot(self):
        for setting in range(1, 11):
            for stage in range(4):
                expected = 1 if stage == 3 else max(1, min(10, (3, 6, 9)[stage] + setting - 5))
                snapshot = resolve(stage, 'progress', setting, 7)
                self.assertEqual(snapshot['profile']['level'], expected)
                self.assertEqual(validate_snapshot(snapshot, stage, 'progress').level, expected)
                if stage == 3:
                    self.assertEqual(resolve(stage, 'omake', setting, 7)['profile']['level'], 10)
                else:
                    with self.assertRaises(DifficultyError): resolve(stage, 'omake', setting, 7)
        original = resolve(1, 'progress', 5, 0)
        for key, value in [('version', True), ('formula_version', 'future'), ('setting', 5.0),
                           ('setting_revision', -1), ('base_level', 9), ('reason', 'omake')]:
            with self.assertRaises(DifficultyError): validate_snapshot(dict(original, **{key: value}), 1)
        for key, value in [('level', True), ('version', 'future'), ('lapse_numerator', 999), ('denominator', 1000.0)]:
            bad = copy.deepcopy(original); bad['profile'][key] = value
            with self.assertRaises(DifficultyError): validate_snapshot(bad, 1)


    def test_protected_fold_and_nondiscard_never_use_lapse_rng(self):
        from types import SimpleNamespace
        from riichienv import ActionType
        from app.mahjong.difficulty import PROFILES, ProfileAgent
        for action_type, fold in ((ActionType.DISCARD, True), (ActionType.TSUMO, False)):
            action = SimpleNamespace(action_type=action_type)
            expert = SimpleNamespace()
            def choose(observation):
                expert.fold = fold
                return action
            expert.choose_action = choose
            for profile in PROFILES:
                agent = ProfileAgent(profile, seed=1)
                agent.expert = expert
                with patch.object(agent.lapse_rng, 'random', side_effect=AssertionError('protected draw')):
                    self.assertIs(agent.choose_action(object()), action)

    def test_all_profiles_public_corpus_golden(self):
        import hashlib
        import json
        from app.mahjong.difficulty import PROFILES, ProfileAgent
        from app.mahjong.riichienv_adapter import RiichiEnvAdapter
        from app.mahjong.tier2 import Tier2Agent
        fixture=json.loads((Path(__file__).parent/'fixtures/difficulty_profiles.json').read_text())
        adapter=RiichiEnvAdapter(seed=fixture['corpus_seed']);adapter.start()
        agents=[Tier2Agent(seed=57010+s) for s in range(4)]
        observations=[]
        while not adapter.done:
            pending=adapter.pending_observations
            observations.extend(pending[s] for s in sorted(pending))
            adapter.step({s:agents[s].choose_action(pending[s]) for s in sorted(pending)})
        observations=observations[::max(1,len(observations)//160)][:160]
        self.assertEqual(len(observations),fixture['corpus_size'])
        for profile, expected in zip(PROFILES,fixture['sequences']):
            agent=ProfileAgent(profile,seed=fixture['agent_seed'],**fixture['personality'])
            sequence=[agent.choose_action(obs).to_dict() for obs in observations]
            self.assertEqual(hashlib.sha256(json.dumps(sequence,sort_keys=True).encode()).hexdigest(),expected['sequence_sha256'])


class LocalDifficultyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='nrnf-difficulty-')
        self.root = Path(self.tmp.name)/'data'
        self.runtime = create_local_runtime(self.root)
        self.runtime.registry._seed_factory = lambda: 5811
        self.client = TestClient(self.runtime.app, raise_server_exceptions=False)
        self.headers = {'X-Local-Capability': self.runtime.capability}

    def tearDown(self):
        self.client.close(); self.runtime.close(); self.tmp.cleanup()

    def put(self, setting, revision=0):
        return self.client.put('/api/local/difficulty', headers=self.headers,
                               json={'setting': setting, 'expected_revision': revision})

    def start(self):
        play = self.client.get('/api/local/play', headers=self.headers).json()
        result = self.client.post('/api/local/play/roster', headers=self.headers,
                                 json={'generation': play['generation'], 'cpu_character_ids': [1,2,3]})
        self.assertEqual(result.status_code, 200, result.text)
        result = self.client.post('/api/game/sessions', headers=self.headers,
                                 json={'generation': play['generation'], 'cpu_character_ids': [1,2,3]})
        self.assertEqual(result.status_code, 201, result.text)
        return result.json(), play

    def test_read_only_strict_revision_commit_failure_and_reset_preserves_setting(self):
        self.assertNotEqual(self.client.get('/api/local/difficulty').status_code, 200)
        self.assertEqual(self.client.get('/api/local/difficulty', headers=self.headers).json()['setting'], 5)
        with self.runtime.session_factory() as session: self.assertIsNone(session.get(GameSetting, KEY))
        for setting in (True, 5.0, '5', 0, 11): self.assertEqual(self.put(setting).status_code, 422)
        self.assertEqual(self.put(8).status_code, 200)
        self.assertEqual(self.put(9).status_code, 409)
        with patch.object(Session, 'commit', side_effect=RuntimeError('test-only commit failure')):
            self.assertEqual(self.put(9,1).status_code, 500)
        self.assertEqual(self.client.get('/api/local/difficulty', headers=self.headers).json()['setting'], 8)
        created, play = self.start()
        self.assertEqual([d['level'] for d in created['cpu_difficulties']], [6,6,6])
        response = self.client.post('/api/local/play/reset', headers=self.headers,
                                   json={'generation':play['generation'], 'confirm':True})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(self.client.get('/api/local/difficulty', headers=self.headers).json()['setting'], 8)
        with self.runtime.session_factory() as session:
            self.assertEqual(session.get(GameSessionRecord, created['session_id']).status, 'cancelled')

    def test_settings_writer_race_and_start_snapshot(self):
        barrier = threading.Barrier(2)
        def save(value):
            barrier.wait()
            return self.put(value).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(save, (2,9)))
        self.assertEqual(sorted(results), [200,409])
        setting = self.client.get('/api/local/difficulty', headers=self.headers).json()
        created, _ = self.start()
        with self.runtime.session_factory() as session:
            choices = session.get(GameSessionRecord,created['session_id']).cpu_choices
            self.assertTrue(all(c['difficulty_snapshot']['setting']==setting['setting'] for c in choices))
            self.assertTrue(all(c['difficulty_snapshot']['setting_revision']==1 for c in choices))

    def test_active_snapshot_replay_after_setting_change_and_completed_restore(self):
        created, play = self.start()
        session_id = created['session_id']
        runtime = self.runtime
        with runtime.session_factory() as session:
            registered = runtime.registry.get_owned(session, session_id, runtime.member_id)
            original_choices = copy.deepcopy(session.get(GameSessionRecord,session_id).cpu_choices)
            for _ in range(12):
                _ack_all_results(session, session_id)
                runtime.registry.submit_action(session, registered, 0, registered.action_version)
                session.commit()
            before = asdict(registered.game.human_turn())
        self.assertEqual(self.put(10).status_code, 200)
        self.assertIs(runtime.registry._games[session_id],registered)
        runtime.registry.evict(session_id)
        with runtime.session_factory() as session:
            restored = runtime.registry.get_owned(session,session_id,runtime.member_id)
            self.assertEqual(asdict(restored.game.human_turn()),before)
            self.assertEqual(session.get(GameSessionRecord,session_id).cpu_choices,original_choices)
            while not registered.game.done:
                self.assertEqual(registered.game.human_turn(),restored.game.human_turn())
                registered.game.submit_human_action(0)
                _ack_all_results(session, session_id)
                runtime.registry.submit_action(session,restored,0,restored.action_version)
                session.commit()
            self.assertEqual(registered.game.result(),restored.game.result())
            runtime.registry.settle(session,restored);session.commit()
            runtime.registry.publish_completed(session,restored)
        with runtime.session_factory() as session:
            done = GameRegistry().get_owned(session,session_id,runtime.member_id)
            self.assertEqual(done.result,registered.game.result())
            self.assertEqual([d['level'] for d in done.cpu_difficulties],[3,3,3])
        # Persisted malformed profiles fail before replay; no rewrite/fallback.
        with runtime.session_factory.begin() as session:
            record=session.get(GameSessionRecord,session_id)
            record.status='active'
            bad=copy.deepcopy(record.cpu_choices);bad[0]['difficulty_snapshot']['profile']['version']='future'
            record.cpu_choices=bad
        with runtime.session_factory() as session:
            with self.assertRaises(Exception): GameRegistry().get_owned(session,session_id,runtime.member_id)
            self.assertEqual(session.get(GameSessionRecord,session_id).cpu_choices[0]['difficulty_snapshot']['profile']['version'],'future')
        runtime.registry.evict(session_id)
        response=self.client.get('/api/game/sessions/active',headers=self.headers)
        self.assertEqual(response.status_code,409,response.text)
        self.assertEqual(response.json()['detail']['code'],'invalid_cpu_snapshot')
        with self.client.websocket_connect(f'/api/game/sessions/{session_id}/ws') as websocket:
            websocket.send_json({'type':'authenticate','capability':runtime.capability,'generation':play['generation']})
            self.assertEqual(websocket.receive_json()['code'],'invalid_cpu_snapshot')


    def test_save_start_race_and_start_commit_failure_preserve_original(self):
        play = self.client.get('/api/local/play', headers=self.headers).json()
        self.client.post('/api/local/play/roster', headers=self.headers,
                         json={'generation':play['generation'], 'cpu_character_ids':[1,2,3]})
        body={'generation':play['generation'], 'cpu_character_ids':[1,2,3]}
        with patch.object(Session, 'commit', side_effect=RuntimeError('test-only start commit failure')):
            failed=self.client.post('/api/game/sessions',headers=self.headers,json=body)
        self.assertEqual(failed.status_code,500)
        self.assertEqual(self.runtime.registry._games,{})
        self.assertIsNone(self.client.get('/api/game/sessions/active',headers=self.headers).json())
        barrier=threading.Barrier(2)
        def start():
            barrier.wait()
            return self.client.post('/api/game/sessions',headers=self.headers,json=body)
        def save():
            barrier.wait()
            return self.put(10)
        with ThreadPoolExecutor(max_workers=2) as pool:
            a,b=pool.submit(start),pool.submit(save)
            started,saved=a.result(),b.result()
        self.assertEqual(started.status_code,201,started.text)
        self.assertEqual(saved.status_code,200,saved.text)
        with self.runtime.session_factory() as session:
            choices=session.get(GameSessionRecord,started.json()['session_id']).cpu_choices
            snapshots=[c['difficulty_snapshot'] for c in choices]
            self.assertEqual(len({s['setting_revision'] for s in snapshots}),1)
            self.assertEqual(len({s['setting'] for s in snapshots}),1)
            self.assertIn((snapshots[0]['setting_revision'],snapshots[0]['setting']),((0,5),(1,10)))
