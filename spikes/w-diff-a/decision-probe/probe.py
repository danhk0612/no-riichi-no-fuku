"""Fixed gate, rotated games, and complete isolated saved-session replay."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import random
import statistics
import sys
import time

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0,str(ROOT/'backend'))
sys.path.insert(0,str(HERE.parent))
from agent import LABELS, PROFILES, ProbeAgent, candidates, validate_profile
from verify import FIELDS, choices, turn_digest
from app.mahjong.riichienv_adapter import RiichiEnvAdapter
from app.mahjong.tier0 import Tier0Agent
from app.mahjong.tier1 import Tier1Agent
from app.mahjong.tier2 import Tier2Agent
from app.services.game_setup import CpuChoice, create_game_session_from_choices
from riichienv import ActionType

BASE = 'e8a70b57db22727a861956ae6ee42c087057f6b8'
CONTEXTS = ('neutral','mixed','characters')
ALL_LABELS = (*LABELS,'tier2')
PERSONALITIES = [{k:p[k] for k in FIELDS} for p in json.loads(
    (ROOT/'backend/app/seeds/cpu_characters.json').read_text())]

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()

def corpus():
    adapter=RiichiEnvAdapter(seed=1701)
    adapter.start()
    agents=[Tier2Agent(seed=17010+s) for s in range(4)]
    observations=[]
    steps=0
    while not adapter.done:
        assert steps < 5000
        pending=adapter.pending_observations
        observations.extend(pending[s] for s in sorted(pending))
        adapter.step({s:agents[s].choose_action(pending[s]) for s in sorted(pending)})
        steps+=1
    assert len(observations)>=160
    return [observations[i*(len(observations)-1)//159] for i in range(160)]

def gate():
    observations=corpus()
    personalities=[*PERSONALITIES,dict.fromkeys(FIELDS,.1),dict.fromkeys(FIELDS,2.)]
    rows, sequences, pools, timings=[],{}, {}, []
    for index,personality in enumerate(personalities):
        for profile in PROFILES:
            agent=ProbeAgent(profile,seed=19001,**personality)
            expert=Tier2Agent(seed=19001,policy_version=2,**personality)
            seq, candidate_seq=[],[]
            changed=protected=folds=ukeire_changes=danger_changes=pool_changes=0
            cpu,wall=[],[]
            types={}
            for obs in observations:
                before,cpu_before=time.perf_counter_ns(),time.process_time_ns()
                action=agent.choose_action(obs)
                cpu.append((time.process_time_ns()-cpu_before)/1e6)
                wall.append((time.perf_counter_ns()-before)/1e6)
                baseline=expert.choose_action(obs)
                assert action.to_dict() in [a.to_dict() for a in obs.legal_actions()]
                assert baseline.to_dict()==agent.last['baseline']
                assert expert._rng.getstate()==agent.expert._rng.getstate()
                if profile.label=='000' or baseline.action_type!=ActionType.DISCARD or agent.expert.fold:
                    assert action.to_dict()==baseline.to_dict()
                    protected+=1
                folds+=agent.expert.fold
                if agent.last['pool']:
                    assert action.to_dict() in agent.last['pool']
                    # Independently reconstruct the unchanged policy's weighted choice.
                    pool=candidates(agent.expert,agent.expert.evaluations)
                    rng=random.Random();rng.setstate(agent.expert.selection_state)
                    weights=[max(1,int(10+agent.expert._compute_expected_value(e,agent.expert.state)*10)) for e in pool]
                    assert rng.choices(pool,weights=weights,k=1)[0].action.to_dict()==baseline.to_dict()
                changed+=action.to_dict()!=baseline.to_dict()
                ukeire_changes+=agent.last['ukeire_changes']
                danger_changes+=agent.last['danger_changes']
                pool_changes+=agent.last['pool']!=agent.last['original_pool']
                types[str(action.action_type)]=types.get(str(action.action_type),0)+1
                seq.append(action.to_dict());candidate_seq.append(agent.last['pool'])
            for k in FIELDS:
                assert getattr(agent.expert,'_'+k)==personality[k]
            sequences[index,profile.label]=seq
            pools[index,profile.label]=candidate_seq
            rows.append(dict(personality=index,label=profile.label,sequence=seq,
                             candidates=candidate_seq,changes=changed,protected=protected,
                             folds=folds,ukeire_changes=ukeire_changes,danger_changes=danger_changes,
                             pool_changes=pool_changes,action_types=types))
            if index==0:
                timings.append(dict(label=profile.label,cpu_mean_ms=statistics.mean(cpu),
                    cpu_p95_ms=sorted(cpu)[151],cpu_max_ms=max(cpu),
                    wall_mean_ms=statistics.mean(wall),wall_p95_ms=sorted(wall)[151],wall_max_ms=max(wall)))
    personality_differences={label:[sum(a!=b for a,b in zip(sequences[0,label],sequences[i,label]))
                                        for i in range(1,8)] for label in LABELS}
    assert all(any(ds[:5]) for ds in personality_differences.values()), 'no character expression'
    assert sum(r['folds'] for r in rows)>0, 'fold boundary unobserved'
    effects=[]
    for bit in range(3):
        for label in LABELS:
            if label[bit]=='1':continue
            high=label[:bit]+'1'+label[bit+1:]
            effects.append(dict(axis='UDM'[bit],low=label,high=high,
                action_differences=[sum(a!=b for a,b in zip(sequences[i,label],sequences[i,high])) for i in range(8)],
                candidate_differences=[sum(a!=b for a,b in zip(pools[i,label],pools[i,high])) for i in range(8)]))
    assert sum(r['ukeire_changes'] for r in rows)>0
    assert sum(r['danger_changes'] for r in rows)>0
    assert any(any(e['action_differences']) for e in effects if e['axis']=='M')
    return dict(base=BASE,corpus_seed=1701,agent_seed=19001,corpus_size=160,
                personalities=personalities,rows=rows,personality_differences=personality_differences,
                axis_effects=effects,timings=timings,gate_passed=True)

def match(job):
    context,label,seed,seat=job
    index=(seed-2000)%6
    personality=PERSONALITIES[0 if context=='neutral' else index]
    agents={}
    for offset in range(4):
        s=(seat+offset)%4
        p=PERSONALITIES[0 if context!='characters' else (index+offset)%6]
        cls=(Tier0Agent,Tier1Agent,Tier2Agent)[offset-1] if context=='mixed' and offset else Tier2Agent
        agents[s]=cls(seed=seed*10+s,**p)
    agents[seat]=(Tier2Agent(seed=seed*10+seat,**personality) if label=='tier2' else
                  ProbeAgent(PROFILES[LABELS.index(label)],seed=seed*10+seat,**personality))
    adapter=RiichiEnvAdapter(seed=seed);adapter.start()
    trace=hashlib.sha256();steps=0;durations=[]
    before=time.perf_counter();changed=folds=nondiscard=0
    while not adapter.done:
        assert steps<5000, ('step budget',job)
        actions={}
        for s in sorted(adapter.pending_observations):
            obs=adapter.pending_observations[s]
            start=time.perf_counter_ns()
            action=agents[s].choose_action(obs)
            assert action.to_dict() in [a.to_dict() for a in obs.legal_actions()]
            actions[s]=action
            if s==seat:
                durations.append((time.perf_counter_ns()-start)/1e6)
                nondiscard+=action.action_type!=ActionType.DISCARD
                if label!='tier2':
                    changed+=action.to_dict()!=agents[s].last['baseline']
                    folds+=agents[s].expert.fold
        trace.update(json.dumps({s:a.to_dict() for s,a in actions.items()},sort_keys=True).encode())
        adapter.step(actions);steps+=1
    result=adapter.result()
    return dict(context=context,label=label,seed=seed,seat=seat,
                personality_index=0 if context=='neutral' else index,
                trace=trace.hexdigest(),scores=result.scores,ranks=result.ranks,steps=steps,
                decisions=len(durations),decision_ms_sum=sum(durations),decision_ms_max=max(durations),
                elapsed_s=time.perf_counter()-before,changed=changed,folds=folds,nondiscard=nondiscard)

def new_game(snapshot,*,current_setting,restoring):
    profile=validate_profile(snapshot['profile'] if restoring else asdict(current_setting))
    def factory(choice,*,seed):
        return ProbeAgent(profile,seed=seed,**{k:getattr(choice,k) for k in FIELDS})
    return create_game_session_from_choices(1,tuple(CpuChoice(**c) for c in snapshot['choices']),
             seed=snapshot['seed'],agent_factory=factory)

def replay():
    rows=[]
    for i,profile in enumerate(PROFILES):
        snapshot=dict(seed=1811,choices=[asdict(c) for c in choices()],profile=asdict(profile))
        game=new_game(snapshot,current_setting=profile,restoring=False)
        history=[]
        for _ in range(12):
            assert not game.done
            game.submit_human_action(0);history.append(0)
        saved=json.loads(json.dumps(dict(snapshot=snapshot,history=history)))
        changed=PROFILES[7-i]
        restored=new_game(saved['snapshot'],current_setting=changed,restoring=True)
        fresh=new_game(saved['snapshot'],current_setting=changed,restoring=False)
        assert all(a.profile==profile for a in restored._cpu_agents.values())
        assert all(a.profile==changed for a in fresh._cpu_agents.values())
        for action in saved['history']:restored.submit_human_action(action)
        trace=[]
        while not game.done:
            assert len(trace)<5000
            value=turn_digest(game)
            assert value==turn_digest(restored)
            trace.append(value)
            game.submit_human_action(0);restored.submit_human_action(0)
        assert restored.done and game.result()==restored.result()
        rows.append(dict(label=profile.label,continuation_turns=len(trace),trace=digest(trace),
                         result=asdict(game.result()),saved_profile_wins=True,fresh_setting=changed.label))
    for value in (dict(label='xxx'),dict(label='000',version='future')):
        try:validate_profile(value)
        except ValueError:pass
        else:raise AssertionError('invalid profile')
    return dict(replay=rows,invalid_profiles_rejected=True)

if __name__=='__main__':
    mode,output=sys.argv[1:]
    value=gate() if mode=='gate' else replay()
    Path(output).write_text(json.dumps(value,indent=2)+'\n')
