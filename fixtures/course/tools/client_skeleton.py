"""Student TCP framing/watchdog example. DOES NOT implement a GNSS solver or GUI.
Replace on_epoch with your own positioning + diagnosis + display workflow.
"""
from __future__ import annotations
import argparse,json,socket,select,time

def on_epoch(epoch:dict)->None:
    # TODO: construct satellite states and pseudorange equations; solve and draw.
    print(f"epoch={epoch['epoch_id']} GPST={epoch['gps_sow']} n={len(epoch['observations'])}",flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--host',default='127.0.0.1');p.add_argument('--port',type=int,default=8765)
    a=p.parse_args();buffer=b'';last=time.monotonic();stale=False;timeout=3.0
    with socket.create_connection((a.host,a.port),timeout=10) as s:
        while True:
            ready,_,_=select.select([s],[],[],.1)
            if not ready:
                if not stale and time.monotonic()-last>timeout:
                    print('TRANSPORT_STALE: last position is historical, not a current fix.',flush=True);stale=True
                continue
            chunk=s.recv(65536)
            if not chunk:
                print('DISCONNECTED',flush=True);break
            last=time.monotonic()
            if stale:print('TRANSPORT_RESUMED',flush=True);stale=False
            buffer+=chunk
            if len(buffer)>1048576:raise ValueError('Frame exceeds 1 MiB')
            while b'\n' in buffer:
                line,buffer=buffer.split(b'\n',1)
                if not line:continue
                obj=json.loads(line.decode('utf8'))
                if obj['type']=='meta':
                    interval=float(obj.get('replay_interval_wall_s',.2));timeout=max(3.,3*interval)
                    print('META',obj,flush=True)
                elif obj['type']=='epoch':on_epoch(obj)
                elif obj['type']=='end':print('END',flush=True);return
                else:raise ValueError('Unsupported record type')

if __name__=='__main__':main()
