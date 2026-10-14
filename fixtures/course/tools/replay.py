"""Replay a GNSS-COURSE JSONL file over localhost TCP. Standard library only.
One connection per run. JSON objects are UTF-8, each terminated by LF.
Input timestamps never change when playback is accelerated.
"""
from __future__ import annotations
import argparse,json,socket,time,csv
from pathlib import Path

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=8765)
    p.add_argument('--interval',type=float,default=.2,help='Wall seconds per epoch; 0 = fastest')
    p.add_argument('--pause-before',type=int,default=-1,help='Pause before this epoch_id')
    p.add_argument('--pause-seconds',type=float,default=5.)
    p.add_argument('--event-log',type=Path)
    a=p.parse_args()
    if a.interval<0 or a.pause_seconds<0:p.error('Intervals must be non-negative')
    objects=[json.loads(s) for s in a.input.read_text(encoding='utf8').splitlines() if s.strip()]
    if not objects or objects[0].get('type')!='meta':p.error('Missing meta record')
    if any(o.get('type')!='epoch' for o in objects[1:]):p.error('Only epoch records may follow meta')
    meta={**objects[0],'replay_interval_wall_s':a.interval}
    logs=[]
    def log(event,eid=-1):logs.append({'monotonic_s':round(time.monotonic(),6),'event':event,'epoch_id':eid})
    try:
        with socket.socket(socket.AF_INET,socket.SOCK_STREAM) as srv:
            srv.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
            srv.bind((a.host,a.port));srv.listen(1)
            print(f'Waiting on {a.host}:{a.port}; input={a.input.name}',flush=True)
            conn,addr=srv.accept()
            with conn:
                conn.settimeout(30);print(f'Connected: {addr}',flush=True);log('CONNECTED')
                def send(obj):conn.sendall((json.dumps(obj,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n').encode('utf8'))
                send(meta)
                for e in objects[1:]:
                    if e['epoch_id']==a.pause_before:
                        print(f'Intentional transport pause: {a.pause_seconds}s',flush=True);log('PAUSE_BEGIN',e['epoch_id']);time.sleep(a.pause_seconds);log('PAUSE_END',e['epoch_id'])
                    send(e);log('EPOCH_SENT',e['epoch_id'])
                    if a.interval:time.sleep(a.interval)
                send({'type':'end','epochs_sent':len(objects)-1});log('END')
                print(f'Sent {len(objects)-1} epochs.',flush=True)
    except (ConnectionError,OSError) as e:
        print(f'Replay stopped: {e}',flush=True);raise SystemExit(1)
    finally:
        if a.event_log:
            a.event_log.parent.mkdir(parents=True,exist_ok=True)
            with a.event_log.open('w',newline='',encoding='utf8') as f:
                w=csv.DictWriter(f,fieldnames=['monotonic_s','event','epoch_id']);w.writeheader();w.writerows(logs)

if __name__=='__main__':main()
