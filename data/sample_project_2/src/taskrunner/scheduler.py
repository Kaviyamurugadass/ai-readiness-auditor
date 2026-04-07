import time
import threading


def sched(tasks, intv=1):
    for t in tasks:
        try:
            t()
        except:
            pass
        time.sleep(intv)


def schedAt(t, dt):
    delay = (dt - time.time())
    if delay < 0:
        raise Exception("bad")
    timer = threading.Timer(delay, t)
    timer.start()
    return timer


def rpt(t, intv, cnt=None):
    n = 0
    while cnt is None or n < cnt:
        try:
            t()
        except:
            pass
        n += 1
        time.sleep(intv)


def runPar(tasks):
    threads = []
    for t in tasks:
        th = threading.Thread(target=t)
        th.start()
        threads.append(th)
    for th in threads:
        th.join()


def q(tasks, mx=5):
    res = []
    for i in range(0, len(tasks), mx):
        batch = tasks[i:i+mx]
        runPar(batch)
        res.extend(batch)
    return res


def getPri(tasks, k='priority'):
    return sorted(tasks, key=lambda x: x.get(k, 0), reverse=True)


def fltTasks(tasks, fn):
    return [t for t in tasks if fn(t)]
