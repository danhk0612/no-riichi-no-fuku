"""Small public-input cost gate and injected-session replay; no product writes."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT/'backend'))
sys.path.insert(0, str(HERE.parent/'decision-probe'))
from probe import FIELDS, PERSONALITIES, choices, turn_digest
from one_step import PROFILES, OneStepAgent, validate_profile, SearchBudgetExceeded
from app.mahjong.tier2 import Tier2Agent
from app.mahjong.riichienv_adapter import RiichiEnvAdapter
from app.services.game_setup import CpuChoice, create_game_session_from_choices
from riichienv import ActionType

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()

def corpus():
    adapter = RiichiEnvAdapter(seed=2701)
    adapter.start()
    agents = [Tier2Agent(seed=27010+s) for s in range(4)]
    obs = []
    steps = 0
    while not adapter.done:
        assert steps < 5000
        pending = adapter.pending_observations
        obs.extend(pending[s] for s in sorted(pending))
        adapter.step({s:agents[s].choose_action(pending[s]) for s in sorted(pending)})
        steps += 1
    assert len(obs) >= 32
    return [obs[i*(len(obs)-1)//31] for i in range(32)]

def gate():
    observations = corpus()
    personalities = [*PERSONALITIES, dict.fromkeys(FIELDS, .1), dict.fromkeys(FIELDS, 2.)]
    rows, timings = [], []
    report = dict(corpus_seed=2701, agent_seed=29001, corpus_size=32,
                  rows=rows, timings=timings, gate_passed=False)
    for index, personality in enumerate(personalities):
        for profile in PROFILES:
            agent = OneStepAgent(profile, seed=29001, **personality)
            expert = Tier2Agent(seed=29001, policy_version=2, **personality)
            sequence, diagnostics, cpu = [], [], []
            row = dict(personality=index, label=profile.label, sequence=sequence, diagnostics=diagnostics)
            rows.append(row)
            for position, obs in enumerate(observations):
                before = time.process_time_ns()
                try:
                    action = agent.choose_action(obs)
                except SearchBudgetExceeded as exc:
                    report['failure'] = dict(type=type(exc).__name__, message=str(exc),
                                             personality=index, label=profile.label, observation=position)
                    return report
                cpu.append((time.process_time_ns()-before)/1e6)
                baseline = expert.choose_action(obs)
                assert action.to_dict() in [a.to_dict() for a in obs.legal_actions()]
                assert baseline.to_dict() == agent.last['baseline']
                assert expert._rng.getstate() == agent.expert._rng.getstate()
                if profile.label == 'baseline' or baseline.action_type != ActionType.DISCARD or agent.expert.fold:
                    assert action.to_dict() == baseline.to_dict()
                for key in FIELDS:
                    assert getattr(agent.expert, '_'+key) == personality[key]
                sequence.append(action.to_dict())
                diagnostics.append(agent.last)
            timings.append(dict(personality=index, label=profile.label,
                                cpu_mean_ms=sum(cpu)/len(cpu), cpu_p95_ms=sorted(cpu)[29], cpu_max_ms=max(cpu)))
    neutral = next(r for r in timings if r['personality']==0 and r['label']=='candidate')
    report['gate_passed'] = neutral['cpu_p95_ms'] <= 250 and neutral['cpu_max_ms'] <= 1000
    if not report['gate_passed']:
        report['failure'] = dict(type='ResearchLatencyGate', message='neutral p95>250ms or max>1000ms')
    return report

def new_game(snapshot, *, current_setting, restoring):
    profile = validate_profile(snapshot['profile'] if restoring else asdict(current_setting))
    def factory(choice, *, seed):
        return OneStepAgent(profile, seed=seed, **{k:getattr(choice, k) for k in FIELDS})
    return create_game_session_from_choices(1, tuple(CpuChoice(**c) for c in snapshot['choices']),
                                           seed=snapshot['seed'], agent_factory=factory)

def replay():
    rows = []
    for index, profile in enumerate(PROFILES):
        snapshot = dict(seed=2811, choices=[asdict(c) for c in choices()], profile=asdict(profile))
        game = new_game(snapshot, current_setting=profile, restoring=False)
        history = []
        for _ in range(12):
            assert not game.done
            game.submit_human_action(0)
            history.append(0)
        saved = json.loads(json.dumps(dict(snapshot=snapshot, history=history)))
        changed = PROFILES[1-index]
        restored = new_game(saved['snapshot'], current_setting=changed, restoring=True)
        fresh = new_game(saved['snapshot'], current_setting=changed, restoring=False)
        assert all(a.profile==profile for a in restored._cpu_agents.values())
        assert all(a.profile==changed for a in fresh._cpu_agents.values())
        for action in saved['history']:
            restored.submit_human_action(action)
        turns = []
        while not game.done:
            assert len(turns) < 5000
            value = turn_digest(game)
            assert value == turn_digest(restored)
            turns.append(value)
            game.submit_human_action(0)
            restored.submit_human_action(0)
        assert restored.done and game.result()==restored.result()
        rows.append(dict(label=profile.label, turns=len(turns), trace=digest(turns),
                         result=asdict(game.result()), saved_profile_wins=True, fresh_setting=changed.label))
    for mutation in (dict(version='future'), dict(blend_numerator=True), dict(node_limit=0)):
        try:
            validate_profile(dict(asdict(PROFILES[1]), **mutation))
        except ValueError:
            pass
        else:
            raise AssertionError('invalid profile accepted')
    return dict(rows=rows, invalid_profiles_rejected=True)

if __name__ == '__main__':
    mode, output = sys.argv[1:]
    result = gate() if mode=='gate' else replay()
    Path(output).write_text(json.dumps(result, indent=2)+'\n')
    if mode=='gate' and not result['gate_passed']:
        raise SystemExit(2)
