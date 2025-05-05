import sys
import json
import itertools as it
from pathlib import Path
from argparse import ArgumentParser
from multiprocessing import Pool, Queue

from mylib import Logger

class ReferenceIterator:
    _keys = (
        'comparison',
        'reference',
    )

    def __init__(self, gt, repetition=1):
        self.gt = gt
        self.repetition = repetition

    def __call__(self, user):
        refs = self.gt.joinpath(user)
        if not refs.exists():
            raise FileNotFoundError(refs)

        for (i, gt) in it.product(range(self.repetition), refs.iterdir()):
            yield dict(zip(self._keys, (i, gt.name)))

def func(incoming, outgoing, args):
    references = ReferenceIterator(
        args.ground_truth,
        args.repetition,
    )

    while True:
        sample = incoming.get()
        config = json.loads(sample)
        try:
            for r in references(config['user']):
                c = dict(config)
                c.update(r)
                outgoing.put(c)
        except FileNotFoundError as err:
            Logger.error('Ground truth not found: %s', err)
        finally:
            outgoing.put(None)

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--ground-truth', type=Path)
    arguments.add_argument('--repetition', type=int, default=1)
    arguments.add_argument('--workers', type=int)
    args = arguments.parse_args()

    incoming = Queue()
    outgoing = Queue()
    initargs = (
        outgoing,
        incoming,
        args,
    )

    with Pool(args.workers, func, initargs):
        jobs = 0
        for i in sys.stdin:
            outgoing.put(i)
            jobs += 1

        while jobs:
            record = incoming.get()
            if record is None:
                jobs -= 1
            else:
                print(json.dumps(record))
