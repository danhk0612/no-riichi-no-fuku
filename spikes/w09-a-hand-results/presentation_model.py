"""Executable proposal only: no product schema/API/UI or actual game settlement."""
import copy, json
from pathlib import Path

def ack(state,generation,event_id):
    if generation!=state['generation']:raise ValueError('stale generation')
    events=state['events']
    index=next(i for i,e in enumerate(events) if e['id']==event_id)
    if index<state['cursor']:return # response lost after successful prior ack
    if index!=state['cursor']:raise ValueError('out of order')
    state['cursor']+=1

def main():
    state={'generation':'g1','session':'s1','cursor':0,'events':[
        {'id':'s1:hand:0','kind':'hand','winners':[1,2]},
        {'id':'s1:hand:1','kind':'hand','winners':[]},
        {'id':'s1:match','kind':'match','stage_before':2,'stage_after':3},
        {'id':'ending-existing-id','kind':'ending'}]}
    checks=[]
    def check(condition,label):
        assert condition,label;checks.append(label)
    # Same persisted payload and cursor after restart; acknowledgements never settle.
    restored=json.loads(json.dumps(state));check(restored==state,'restart preserves all unshown hands before match and ending')
    try:ack(state,'g1','s1:match')
    except ValueError:checks.append('cannot acknowledge match before final hand')
    else:raise AssertionError('order bypass')
    for event in state['events']:
        before=copy.deepcopy(state['events'])
        ack(state,'g1',event['id']);cursor=state['cursor']
        state=json.loads(json.dumps(state)) # ack commit succeeded, response lost/restart
        ack(state,'g1',event['id'])
        check(state['cursor']==cursor,'ack response loss is idempotent: '+event['id'])
        check(state['events']==before,'ack never changes stage/content: '+event['id'])
    state['generation']='g2'
    try:ack(state,'g1','s1:hand:0')
    except ValueError:checks.append('reset rejects late prior generation ack')
    else:raise AssertionError('generation bypass')
    (Path(__file__).parent/'evidence/presentation-model.json').write_text(json.dumps(dict(
        scope='pure synthetic proposal, not existing product persistence/UI coverage',checks=checks),indent=2)+'\n')
    print(f'{len(checks)} proposal assertions passed')
if __name__=='__main__':main()
