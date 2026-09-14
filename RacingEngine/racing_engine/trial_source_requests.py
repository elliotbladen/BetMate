"""Bounded public-source requests: preserve checkpoints and stop on access refusal."""
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import json
import re
from threading import Event, Lock
import time
from urllib.error import HTTPError
from .storage import utc_now

class SourceAccessStopped(RuntimeError):
    pass

class SourceGate:
    def __init__(self, checkpoint, interval=1.0):
        self.checkpoint=checkpoint;self.interval=interval;self.lock=Lock();self.stopped=Event();self.last=0.0
    def stop(self,reason):
        with self.lock:
            if self.stopped.is_set():raise SourceAccessStopped(reason)
            self.stopped.set()
            self.checkpoint.write_text(json.dumps({'status':'access_blocked','reason':reason,'observed_at':utc_now(),'action':'requests_stopped; resume only after normal access is restored'},indent=2)+'\n')
        raise SourceAccessStopped(reason)
    def call(self,fn,*args,**kwargs):
        with self.lock:
            if self.stopped.is_set():raise SourceAccessStopped('source_access_already_stopped')
            time.sleep(max(0,self.interval-(time.monotonic()-self.last)));self.last=time.monotonic()
        if self.stopped.is_set():raise SourceAccessStopped('source_access_already_stopped')
        try:result=fn(*args,**kwargs)
        except HTTPError as exc:
            if exc.code in {401,403,429}:self.stop('HTTP_'+str(exc.code))
            raise
        if isinstance(result,bytes) and re.search(br'<title>\s*(?:Are you human\?|Access Denied|Just a moment)',result,re.I):self.stop('source_access_challenge')
        return result

def bounded_map(fn,items,workers=4):
    """Never queue an entire archive; cancel unstarted work on the first fatal error."""
    pool=ThreadPoolExecutor(max_workers=workers);it=iter(items);pending=deque()
    try:
        for _ in range(workers):
            item=next(it,None)
            if item is not None:pending.append(pool.submit(fn,item))
        while pending:
            yield pending.popleft().result()
            item=next(it,None)
            if item is not None:pending.append(pool.submit(fn,item))
    finally:pool.shutdown(wait=True,cancel_futures=True)
