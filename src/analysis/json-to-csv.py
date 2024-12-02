import sys
import csv
import json
import functools as ft
from typing import Union
from pathlib import Path
from argparse import ArgumentParser
from multiprocessing import Pool, Queue

from mylib import Logger

#
#
#
@ft.singledispatch
def extract(value):
    raise TypeError(type(value))

@extract.register(str)
@extract.register(int)
def _(element: Union[str, int]):
    return element

#
#
#
def parse(collection):
    for (k, v) in collection.items():
        try:
            v = extract(v)
        except TypeError:
            continue
        yield (k, v)

def func(incoming, outgoing, nchars):
    while True:
        result = incoming.get()
        # Logger.info(result)

        data = json.loads(result)
        if nchars is not None:
            for i in ('system', 'user'):
                data[i] = data[i][:nchars]
            docs = Path(data['docs'])
            docs = docs.parent.joinpath(docs.name[:nchars])
            data['docs'] = str(docs)
        score = data['judgement']['score']

        outgoing.put(dict(parse(data), score=score))

#
#
#
if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--name-length', type=int)
    arguments.add_argument('--workers', type=int)
    args = arguments.parse_args()

    incoming = Queue()
    outgoing = Queue()
    initargs = (
        outgoing,
        incoming,
        args.name_length,
    )

    with Pool(args.workers, func, initargs):
        jobs = 0
        for i in sys.stdin:
            outgoing.put(i)
            jobs += 1

        writer = None
        for _ in range(jobs):
            row = incoming.get()
            if writer is None:
                writer = csv.DictWriter(sys.stdout, fieldnames=row)
                writer.writeheader()
            writer.writerow(row)
