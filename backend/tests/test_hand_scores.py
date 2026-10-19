import hashlib
import json
import unittest
from dataclasses import FrozenInstanceError, replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, PropertyMock, patch

from riichienv import ActionType, Meld, MeldType, convert, parse_hand

from app.mahjong.hand_scores import HandScoreCaptureError, _score, capture_hand_scores
from app.mahjong.riichienv_adapter import RiichiEnvAdapter
from app.mahjong.tier0 import Tier0Agent
from app.mahjong.tier2 import Tier2Agent


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def fixture(winners=(1,), hand='123456m789p2234s', tile='5s', tsumo=False,
            honba=0, sticks=0, last_tile=False, melds=()):
    """Synthetic public-API legal decision; never saved user data."""
    pool = [convert.tid_to_mjai(i) for i in range(136)]
    hands = [None] * 4
    for seat in winners:
        text = '123456m66789p34s' if len(winners) == 3 and seat == winners[-1] else hand
        hands[seat] = [convert.tid_to_mjai(t) for t in parse_hand(text)[0]]
        for item in hands[seat]:
            pool.remove(item)
    for meld in melds:
        for item in meld.tiles:
            pool.remove(convert.tid_to_mjai(item))
    pool.remove(tile)
    for seat in range(4):
        if hands[seat] is None:
            hands[seat] = [pool.pop(0) for _ in range(13)]
    adapter = RiichiEnvAdapter(seed=701)
    adapter.start()
    env = adapter._env
    env.apply_event(dict(type='start_kyoku', bakaze='E', kyoku=1, honba=honba,
                         kyotaku=sticks, oya=0, scores=[25000]*4,
                         dora_marker=pool.pop(0), tehais=hands))
    env.is_first_turn = False
    if melds:
        configured = env.melds
        configured[winners[0]] = list(melds)
        env.melds = configured
    actor = winners[0] if tsumo else next(s for s in range(4) if s not in winners)
    if last_tile:
        draws = [t for t in pool if t != tile][:69]
        assert len(draws) == 69
        for i, drawn in enumerate(draws):
            player = (actor - 69 + i) % 4
            env.apply_event(dict(type='tsumo', actor=player, pai=drawn))
            env.apply_event(dict(type='dahai', actor=player, pai=drawn, tsumogiri=True))
    env.apply_event(dict(type='tsumo', actor=actor, pai=tile))
    if not tsumo:
        env.apply_event(dict(type='dahai', actor=actor, pai=tile, tsumogiri=True))
    adapter._observations = {s:o for s,o in env.get_observations().items() if o.legal_actions()}
    return adapter


def winning_actions(adapter, winners, tsumo=False):
    actions = {}
    for seat in adapter.pending_observations:
        wanted = ActionType.TSUMO if tsumo and seat in winners else ActionType.RON if seat in winners else ActionType.PASS
        actions[seat] = next(a for a in adapter.legal_actions(seat) if a.action_type == wanted)
    assert set(winners) <= set(actions)
    return actions


class HandScoresTest(unittest.TestCase):
    def verify_fixture(self, adapter, winners=(1,), tsumo=False):
        env = adapter._env
        actions = winning_actions(adapter, winners, tsumo)
        before = (env.mjai_log, env.hands, env.wall, env.scores(), env.pao)
        captured = capture_hand_scores(env, actions)
        self.assertEqual(before, (env.mjai_log, env.hands, env.wall, env.scores(), env.pao))
        adapter.step(actions)
        self.assertEqual(adapter.last_hand_wins, captured.verify(env))
        expected = () if len(winners) == 3 else winners
        self.assertEqual({w.actor for w in adapter.last_hand_wins}, set(expected))
        for win in adapter.last_hand_wins:
            self.assertEqual(env.mjai_log[win.hand_start_offset]['type'], 'start_kyoku')
            event = env.mjai_log[win.hora_offset]
            self.assertEqual(tuple(event['deltas']), win.deltas)
            self.assertEqual(event['target'], win.target)
            with self.assertRaises(FrozenInstanceError):
                win.actor = 3
        return adapter.last_hand_wins

    def test_ordinary_parent_child_ron_tsumo_with_bonus(self):
        for actor in (0, 1):
            for tsumo in (False, True):
                for honba, sticks in ((0, 0), (3, 2)):
                    with self.subTest(actor=actor, tsumo=tsumo, honba=honba):
                        a = fixture((actor,), tsumo=tsumo, honba=honba, sticks=sticks)
                        win = self.verify_fixture(a, (actor,), tsumo)[0]
                        self.assertEqual(win.score.band, 1)
                        self.assertFalse(win.score.yakuman)

    def test_double_ron_source_order_and_triple_ron_draw(self):
        for winners in ((1, 2), (1, 2, 3)):
            with self.subTest(winners=winners):
                a = fixture(winners, honba=3, sticks=2)
                wins = self.verify_fixture(a, winners)
                self.assertEqual([w.actor for w in wins], [e['actor'] for e in a._env.mjai_log if e['type'] == 'hora'])
                if not wins:
                    self.assertTrue(any(e['type'] == 'ryukyoku' for e in a._env.mjai_log))

    def test_grades_exclude_payment_bonus(self):
        for han, fu, expected in ((4,30,1), (4,40,2), (5,30,2), (6,30,2), (7,30,2), (8,30,3), (10,30,3), (11,30,3), (12,30,3), (13,30,3)):
            with self.subTest(han=han, fu=fu):
                value = SimpleNamespace(is_win=True, han=han, fu=fu, yakuman=False, yaku=[14],
                                        ron_agari=999999, tsumo_agari_oya=999999, tsumo_agari_ko=999999, pao_payer=None)
                self.assertEqual(_score(value).band, expected)
        for hand, tile, expected in (('123m123p123s111z9s','9s',2), ('1122334455667m','7m',3), ('19m19p19s1234567z','1m',3)):
            self.assertEqual(self.verify_fixture(fixture(hand=hand, tile=tile))[0].score.band, expected)

    def test_last_draw_discard_yaku(self):
        for name, tsumo, yaku in (('haitei',True,5), ('houtei',False,6)):
            with self.subTest(name=name):
                self.assertIn(yaku, self.verify_fixture(fixture(tsumo=tsumo, last_tile=True), tsumo=tsumo)[0].score.yaku)

    def test_rinshan_after_legal_ankan(self):
        a = fixture(hand='1111z123m456p78s2p', tile='2p', tsumo=True)
        env = a._env
        available = list(range(136))
        unique_hands = []
        # MJAI strings normalize copies; kan consumption needs distinct physical IDs.
        for hand in env.hands:
            unique = []
            for tile in hand:
                name = convert.tid_to_mjai(tile)
                physical = next(t for t in available if convert.tid_to_mjai(t) == name)
                available.remove(physical)
                unique.append(physical)
            unique_hands.append(unique)
        env.hands = unique_hands
        drawn = next(t for t in available if convert.tid_to_mjai(t) == '9s')
        available.remove(drawn)
        env.wall = [drawn, *available]
        a._observations = {s:o for s,o in env.get_observations().items() if o.legal_actions()}
        ankan = next(x for x in a.legal_actions(1) if x.action_type == ActionType.ANKAN)
        a.step({1: ankan})
        self.assertTrue(env.is_rinshan_flag)
        self.assertEqual(a.last_hand_wins, ())
        self.assertIn(4, self.verify_fixture(a, tsumo=True)[0].score.yaku)

    def test_pao_parent_child_ron_tsumo(self):
        dragons = tuple(Meld(MeldType.Pon, list(parse_hand(t)[0]), True) for t in ('555z','666z','777z'))
        for actor in (0, 1):
            for tsumo in (False, True):
                with self.subTest(actor=actor, tsumo=tsumo):
                    a = fixture((actor,), hand='123m9p', tile='9p', tsumo=tsumo, honba=2, sticks=1, melds=dragons)
                    pao = a._env.pao
                    pao[actor] = {37: 2}
                    a._env.pao = pao
                    win = self.verify_fixture(a, (actor,), tsumo)[0]
                    self.assertEqual(win.score.pao_payer, 2)
                    self.assertIn(37, win.score.yaku)
                    self.assertEqual(win.score.band, 3)
                    self.assertEqual(win.deltas[3], 0)
                    base = 48000 if actor == 0 else 32000
                    self.assertEqual(win.deltas[actor], base + 600 + 1000)
                    self.assertEqual(win.deltas[2], -(base + 600) if tsumo else -(base // 2 + 600))

    def test_chankan_engine_establishes_pending_kan(self):
        pool = [convert.tid_to_mjai(i) for i in range(136)]
        hands = [[convert.tid_to_mjai(t) for t in parse_hand(h)[0]]
                 for h in ('123m456p789s1z', '123456m789p2234s')]
        for hand in hands:
            for tile in hand:
                pool.remove(tile)
        base = convert.mpsz_to_tid('5s') // 4 * 4
        for i in range(4):
            pool.remove(convert.tid_to_mjai(base + i))
        hands += [[pool.pop(0) for _ in range(13)] for _ in range(2)]
        a = RiichiEnvAdapter(seed=701)
        a.start()
        env = a._env
        env.apply_event(dict(type='start_kyoku', bakaze='E', kyoku=1, honba=0,
                             kyotaku=0, oya=0, scores=[25000]*4,
                             dora_marker=pool.pop(0), tehais=hands))
        melds = env.melds
        melds[0] = [Meld(MeldType.Pon, [base+i for i in (1,2,3)], True)]
        env.melds = melds
        env.is_first_turn = False
        env.apply_event(dict(type='tsumo', actor=0, pai=convert.tid_to_mjai(base)))
        a._observations = {s:o for s,o in env.get_observations().items() if o.legal_actions()}
        kakan = next(x for x in a.legal_actions(0) if x.action_type == ActionType.KAKAN)
        a.step({0:kakan})
        self.assertEqual(a.last_hand_wins, ())
        self.assertIn(3, self.verify_fixture(a)[0].score.yaku)

    def test_mismatch_never_falls_back(self):
        a = fixture()
        actions = winning_actions(a, (1,))
        captured = capture_hand_scores(a._env, actions)
        with self.assertRaises(HandScoreCaptureError):
            replace(captured, expected_horas=('wrong',)).verify(a._env)
        before = a._env.mjai_log
        with patch('app.mahjong.riichienv_adapter.capture_hand_scores', side_effect=ValueError('fixture')):
            with self.assertRaises(HandScoreCaptureError):
                a.step(actions)
        self.assertEqual(a._env.mjai_log, before)
        with patch('app.mahjong.riichienv_adapter.capture_hand_scores', return_value=replace(captured,expected_horas=('wrong',))):
            with self.assertRaises(HandScoreCaptureError):
                a.step(actions)
        self.assertEqual(a.last_hand_wins, ())

    def test_missing_engine_result_is_rejected(self):
        a = fixture()
        proxy = Mock(wraps=a._env)
        proxy.mjai_log = a._env.mjai_log
        real_clone = a._env.clone()
        clone = Mock(wraps=real_clone)
        type(clone).mjai_log = PropertyMock(side_effect=lambda: real_clone.mjai_log)
        clone.win_results = {}
        proxy.clone.return_value = clone
        with self.assertRaisesRegex(HandScoreCaptureError, 'identities differ'):
            capture_hand_scores(proxy, winning_actions(a, (1,)))

    def test_natural_baselines_and_result_offsets(self):
        root = Path(__file__).resolve().parents[2]
        for tier, agent in ((0,Tier0Agent), (2,Tier2Agent)):
            with self.subTest(tier=tier):
                a = RiichiEnvAdapter(seed=701)
                a.start()
                agents = {s:agent(seed=7010+s) for s in range(4)}
                trace, wins = [], []
                intermediate = final = 0
                while not a.done:
                    actions = {s:agents[s].choose_action(o) for s,o in a.pending_observations.items()}
                    trace.append({str(s):x.to_dict() for s,x in actions.items()})
                    a.step(actions)
                    if not any(x.action_type in (ActionType.RON, ActionType.TSUMO) for x in actions.values()):
                        self.assertEqual(a.last_hand_wins, ())
                    wins.extend(a.last_hand_wins)
                    if a.last_hand_wins:
                        if a._env.win_results:
                            final += 1
                        else:
                            intermediate += 1
                expected = json.loads((root/f'spikes/w09-a-hand-results/evidence/701-tier{tier}-0.json').read_text())
                self.assertEqual(len(trace), expected['steps'])
                self.assertEqual(digest(trace), expected['trace'])
                self.assertEqual(list(a.result().scores), expected['scores'])
                self.assertEqual(list(a.result().ranks), expected['ranks'])
                self.assertEqual(digest(a._env.mjai_log), expected['log_digest'])
                self.assertEqual(len(wins), sum(e['type']=='hora' for e in a._env.mjai_log))
                self.assertGreater(intermediate, 0)
                self.assertEqual(final, 1)
                self.assertTrue(all(w.hand_start_offset < w.hora_offset for w in wins))
