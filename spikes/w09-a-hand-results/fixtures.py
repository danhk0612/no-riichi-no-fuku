"""Isolated public-API fixtures; no new natural seeds or engine patches."""
import json, time, traceback
from pathlib import Path
from riichienv import RiichiEnv, GameRule, convert, calculate_score
from diagnose import digest

def multi_fixture():
    # Two different closed sanshoku hands, both waiting on 9s. Tile inventory <=4.
    waits=[['1m','2m','3m','1p','2p','3p','1s','2s','3s','E','E','E','9s'],
           ['4m','5m','6m','4p','5p','6p','4s','5s','6s','S','S','S','9s']]
    pool=[convert.tid_to_mjai(i) for i in range(136)]
    for hand in waits:
        for t in hand:pool.remove(t)
    pool.remove('9s');h0=[pool.pop(0) for _ in range(13)];h3=[pool.pop(0) for _ in range(13)]
    start=dict(type='start_kyoku',bakaze='E',kyoku=1,honba=0,kyotaku=0,oya=0,
               scores=[25000]*4,dora_marker=pool.pop(0),tehais=[h0,waits[0],waits[1],h3])
    e=RiichiEnv(game_mode='4p-red-east',rule=GameRule.default_tenhou(),seed=701)
    e.reset()
    for event in [start,dict(type='tsumo',actor=0,pai='9s'),dict(type='dahai',actor=0,pai='9s',tsumogiri=True)]:e.apply_event(event)
    observations=e.get_observations()
    offered={s:[a.to_dict() for a in o.legal_actions()] for s,o in observations.items()}
    from riichienv import ActionType
    actions={}
    for s,o in observations.items():
        legal=o.legal_actions()
        if not legal:continue
        actions[s]=next((a for a in legal if a.action_type==ActionType.RON),next((a for a in legal if a.action_type==ActionType.PASS),legal[0]))
    e.step(actions)
    return dict(offered=offered,chosen={s:a.to_dict() for s,a in actions.items()},
                hora=[x for x in e.mjai_log if x['type']=='hora'],win_results={s:dict(han=w.han,fu=w.fu) for s,w in e.win_results.items()},
                sanchaho_is_draw=GameRule.default_tenhou().sanchaho_is_draw)

def main():
    started=time.monotonic();result={'kind':'synthetic public API; not natural sample'}
    result['score_api']=[]
    for is_oya in (False,True):
        for tsumo in (False,True):
            for han,fu,band in [(3,60,1),(3,70,2),(4,30,1),(4,40,2),(5,30,2),(7,30,2),(8,30,3),(11,30,3),(13,30,3)]:
                values=[]
                for honba in (0,3):
                    s=calculate_score(han,fu,is_oya,tsumo,honba)
                    values.append({k:getattr(s,k) for k in ('total','pay_ron','pay_tsumo_oya','pay_tsumo_ko')})
                zero=calculate_score(han,fu,False,False,0).pay_ron
                assert (3 if zero>=16000 else 2 if zero>=8000 else 1)==band
                result['score_api'].append(dict(han=han,fu=fu,is_oya=is_oya,tsumo=tsumo,expected_band=band,score_without_bonus=values[0],with_3_honba=values[1]))
    try:result['double_ron']=multi_fixture()
    except BaseException:result['double_ron_error']=traceback.format_exc()
    from riichienv import HandEvaluator, Conditions, parse_tile
    y=HandEvaluator.hand_from_text('19m19p19s1234567z').calc(parse_tile('1m'),conditions=Conditions())
    result['standalone_evaluator_yakuman']={k:getattr(y,k) for k in ('is_win','yakuman','han','fu','ron_agari','pao_payer')}
    result['yakuman_scope']='standalone evaluator defaults; not default_tenhou end-to-end verification'
    result['elapsed_s']=time.monotonic()-started
    (Path(__file__).parent/'evidence/fixtures.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result.get('double_ron',result.get('double_ron_error')),indent=2))
if __name__=='__main__':main()
