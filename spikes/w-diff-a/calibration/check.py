"""Common public observations, protected decisions, complete saved replay and timing."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time
from run import PERSONALITIES, match
from profiles_v2 import PROFILES, ProfileAgent
from profiles import PROFILES as V1, ProfileAgent as AgentV1
from verify import FIELDS, choices, turn_digest
from app.mahjong.riichienv_adapter import RiichiEnvAdapter
from app.mahjong.tier2 import Tier2Agent
from app.services.game_setup import CpuChoice, create_game_session_from_choices
from riichienv import ActionType, calculate_shanten

def corpus():
    adapter = RiichiEnvAdapter(seed=701)
    adapter.start()
    agents = [Tier2Agent(seed=7010+s) for s in range(4)]
    observations = []
    while not adapter.done:
        pending = adapter.pending_observations
        observations.extend(pending[s] for s in sorted(pending))
        adapter.step({s:agents[s].choose_action(pending[s]) for s in sorted(pending)})
    return observations[::max(1,len(observations)//160)][:160]

def new_game(snapshot, *, current_setting, restoring):
    candidate = snapshot['profile'] if restoring else asdict(current_setting)
    if candidate not in [asdict(p) for p in PROFILES]:
        raise ValueError('unknown immutable v2 profile')
    profile = PROFILES[candidate['level']-1]
    def factory(choice, *, seed):
        return ProfileAgent(profile, seed=seed, **{k:getattr(choice,k) for k in FIELDS})
    return create_game_session_from_choices(1,tuple(CpuChoice(**c) for c in snapshot['choices']),
        seed=snapshot['seed'],agent_factory=factory)

def check():
    observations = corpus()
    personalities = [*PERSONALITIES,dict.fromkeys(FIELDS,.1),dict.fromkeys(FIELDS,2.)]
    rows, sequences, timings = [], {}, []
    for index, personality in enumerate(personalities):
        for profile in PROFILES:
            agents = [ProfileAgent(profile,seed=9001,**personality) for _ in range(2)]
            v1 = AgentV1(V1[profile.level-1],seed=9001,**personality)
            expert = Tier2Agent(seed=9001,policy_version=2,**personality)
            seq, baseline_seq = [], []
            excess_sum = v1_excess_sum = discard_count = protected = 0
            cpu, wall = [], []
            for obs in observations:
                before, before_cpu = time.perf_counter_ns(),time.process_time_ns()
                action = agents[0].choose_action(obs)
                cpu.append((time.process_time_ns()-before_cpu)/1e6)
                wall.append((time.perf_counter_ns()-before)/1e6)
                other = agents[1].choose_action(obs)
                baseline = expert.choose_action(obs)
                old = v1.choose_action(obs)
                assert action.to_dict()==other.to_dict()
                assert action.to_dict() in [a.to_dict() for a in obs.legal_actions()]
                assert baseline.to_dict()==agents[0].last_selected.to_dict()
                if profile.level==10 or baseline.action_type!=ActionType.DISCARD or agents[0].expert.fold:
                    assert action.to_dict()==baseline.to_dict()
                    protected += 1
                if baseline.action_type==ActionType.DISCARD:
                    by_tile = {}
                    for a in obs.legal_actions():
                        if a.action_type==ActionType.DISCARD:
                            hand=list(obs.hand);hand.remove(a.tile)
                            by_tile[a.tile]=calculate_shanten(hand)
                    best=min(by_tile.values())
                    excess_sum+=by_tile[action.tile]-best
                    v1_excess_sum+=by_tile[old.tile]-best
                    discard_count+=1
                    if action.to_dict()!=baseline.to_dict():
                        assert by_tile[action.tile]<=best+profile.max_shanten_excess
                        assert len(agents[0].last_pool)<=profile.max_tile_kinds
                        assert action.to_dict() in [e.action.to_dict() for e in agents[0].last_pool]
                seq.append(action.to_dict());baseline_seq.append(baseline.to_dict())
            for k in FIELDS:
                assert getattr(agents[0].expert,'_'+k)==personality[k]
            sequences[index,profile.level]=seq
            row=dict(personality=index,level=profile.level,decisions=len(seq),
                sequence_sha256=hashlib.sha256(json.dumps(seq,sort_keys=True).encode()).hexdigest(),
                differences_from_expert=sum(a!=b for a,b in zip(seq,baseline_seq)),
                protected_decisions=protected,protected_folds=agents[0].protected_folds,
                discard_count=discard_count,shanten_excess_sum=excess_sum,v1_shanten_excess_sum=v1_excess_sum,
                lapses=agents[0].lapses,changed=agents[0].changed)
            rows.append(row)
            if index==0:
                timings.append(dict(level=profile.level,cpu_mean_ms=statistics.mean(cpu),
                    cpu_p95_ms=sorted(cpu)[int((len(cpu)-1)*.95)],cpu_max_ms=max(cpu),
                    wall_mean_ms=statistics.mean(wall)))
    personality_differences = {str(l):[sum(a!=b for a,b in zip(sequences[0,l],sequences[i,l]))
                                      for i in range(1,6)] for l in range(1,11)}
    adjacent = {str(i):[sum(a!=b for a,b in zip(sequences[i,l],sequences[i,l+1]))
                       for l in range(1,10)] for i in range(8)}
    assert all(all(d) for d in adjacent.values()), adjacent
    replay=[]
    for profile in PROFILES:
        snapshot=dict(seed=811,choices=[asdict(c) for c in choices()],profile=asdict(profile))
        game=new_game(snapshot,current_setting=profile,restoring=False)
        history=[]
        for _ in range(12):
            assert not game.done
            history.append(0);game.submit_human_action(0)
        saved=json.loads(json.dumps(dict(snapshot=snapshot,history=history)))
        changed=PROFILES[10-profile.level]
        restored=new_game(saved['snapshot'],current_setting=changed,restoring=True)
        fresh=new_game(saved['snapshot'],current_setting=changed,restoring=False)
        assert all(a.profile==profile for a in restored._cpu_agents.values())
        assert all(a.profile==changed for a in fresh._cpu_agents.values())
        for action in saved['history']:restored.submit_human_action(action)
        turns=0
        while not game.done:
            assert turn_digest(game)==turn_digest(restored)
            game.submit_human_action(0);restored.submit_human_action(0);turns+=1
        assert restored.done and game.result()==restored.result()
        replay.append(dict(level=profile.level,continuation_turns=turns,result=asdict(game.result()),
                           saved_profile_wins=True,fresh_uses_changed_setting=True))
    for mutation in (dict(version='future'),dict(lapse_numerator=999),dict(level=0)):
        try:new_game(dict(snapshot,profile=dict(snapshot['profile'],**mutation)),current_setting=PROFILES[0],restoring=True)
        except ValueError:pass
        else:raise AssertionError('invalid profile accepted')
    return dict(corpus_seed=701,agent_seed=9001,corpus_size=len(observations),
        personalities=personalities,common_input=rows,personality_different_actions=personality_differences,
        adjacent_different_actions=adjacent,timings=timings,replay=replay,invalid_profiles_rejected=True)

if __name__=='__main__':
    Path(sys.argv[1]).write_text(json.dumps(check(),indent=2)+'\n')
