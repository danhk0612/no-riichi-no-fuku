"""Analyze saved bounded samples only. Never adds/retries natural games."""
import json
from pathlib import Path
from collections import Counter
from diagnose import digest
HERE=Path(__file__).resolve().parent

def main():
    rows=[json.loads(p.read_text()) for p in sorted((HERE/'evidence').glob('*-1.json'))]
    report=dict(natural_pairs=8,trace_equal=True,rounds=0,horas=0,draw_events=0,
                intermediate_win_results_missing=0,final_win_results_present=0,
                observation_hora_copies=0,native_final_semantic_mismatches=[],viewer_final_bonus_differences=[],
                viewer_final_semantics_equal=0,candidates={},samples=[])
    for r in rows:
        base=json.loads((HERE/'evidence'/f'{r["seed"]}-tier{r["tier"]}-0.json').read_text())
        assert all(r[k]==base[k] for k in ('trace','scores','ranks','steps','log_digest'))
        report['rounds']+=r['event_counts']['start_kyoku'];report['horas']+=r['event_counts'].get('hora',0)
        report['draw_events']+=r['event_counts'].get('ryukyoku',0);report['observation_hora_copies']+=len(r['observation_hora'])
        for b in r['boundaries']:
            if not b['done'] and any(e['type']=='hora' for e in b['events']):
                report['intermediate_win_results_missing']+=not b['win_results']
        final=r['boundaries'][-1]['win_results']
        if final:report['final_win_results_present']+=1
        native={str(c['seat']):c['actual'] for c in r['native'][-1]}
        semantic=('is_win','han','fu','yakuman','yaku')
        if any(any(actual[k]!=native[seat][k] for k in semantic) for seat,actual in final.items()):
            report['native_final_semantic_mismatches'].append(dict(seed=r['seed'],tier=r['tier'],live=final,replay=native))
        viewer=r['viewer'][-1]
        assert len(final)==len(viewer)
        if final:
            equal=all(all(actual[k]==v[k] for k in semantic) for actual,v in zip(final.values(),viewer))
            report['viewer_final_semantics_equal']+=equal
            if any(actual!=v for actual,v in zip(final.values(),viewer)):
                report['viewer_final_bonus_differences'].append(dict(seed=r['seed'],tier=r['tier'],live=final,viewer=viewer))
        report['samples'].append(dict(seed=r['seed'],tier=r['tier'],steps=r['steps'],elapsed_s=r['elapsed_s'],
                                     native_s=r['native_s'],viewer_s=r['viewer_s'],trace=r['trace'],
                                     counts=r['event_counts'],log_digest=r['log_digest']))
    report['candidates']={
        'live_win_results_after_step':'not sufficient: intermediate results already cleared',
        'native_replay':'adoption stopped at first evaluated sample: extra yaku/han; no repair/tuning',
        'viewer_raw_win_result':'not a drop-in: honba/riichi excluded, no winner seat field; conditional scoring recheck required',
        'viewer_han_fu_plus_official_score':'not adopted: final semantic agreement is limited evidence; intermediate/special scoring not independently proven',
        'mjai_log_identity':'recommend only as result identity/source ordering, not score inference'}
    report['candidate_policy']='fixed batch completed before offline candidate comparison; rejection does not discard later archived evidence'
    (HERE/'evidence/analysis.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('samples','native_final_semantic_mismatches','viewer_final_bonus_differences')},indent=2))
if __name__=='__main__':main()
