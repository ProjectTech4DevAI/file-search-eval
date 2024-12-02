import sys
import json
from pathlib import Path
from argparse import ArgumentParser
from multiprocessing import Pool, Queue

from mylib import Logger

def func(incoming, outgoing, gt):
    while True:
        experiment = incoming.get()

        config = json.loads(experiment)
        target = gt.joinpath(config['user'])
        if target.exists():
            Logger.info(experiment.name)
            record = config
        else:
            Logger.warning('No ground truth: %s', experiment.name)
            record = None

        outgoing.put(record)

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--ground-truth', type=Path)
    arguments.add_argument('--workers', type=int)
    args = arguments.parse_args()

    incoming = Queue()
    outgoing = Queue()
    initargs = (
        outgoing,
        incoming,
        args.ground_truth,
    )

    with Pool(args.workers, func, initargs):
        jobs = 0
        for i in sys.stdin:
            queue.put(i)
            jobs += 1

        for _ in range(jobs):
            record = incoming.get()
            if record is not None:
                print(json.dumps(record))
