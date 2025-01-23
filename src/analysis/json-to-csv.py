import sys
import csv
import json
import functools as ft
from typing import Union
from pathlib import Path
from argparse import ArgumentParser
from multiprocessing import Pool, Queue

from mylib import Logger, ResponseJudgement

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
class ScoreHandler:
    def __init__(self, method):
        self.method = method

    def __call__(self, judgements):
        for j in judgements:
            response = ResponseJudgement(**j)
            if response.method == self.method:
                return response.score

        raise ValueError(f'Unknown method: {self.method}')
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

def func(incoming, outgoing, args):
    prompts = (
        # 'system',
        'user',
    )

    while True:
        result = incoming.get()
        # Logger.info(result)

        data = json.loads(result)
        view = dict(parse(data))

        if args.name_length is not None:
            for i in prompts:
                data[i] = data[i][:args.name_length]

        records = []
        for j in data['judgement']:
            response = ResponseJudgement(**j)
            rec = dict(view)
            rec.update({
                'method': response.method,
                'score': response.score,
            })
            records.append(rec)

        outgoing.put(records)

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
        args,
    )

    with Pool(args.workers, func, initargs):
        jobs = 0
        for i in sys.stdin:
            outgoing.put(i)
            jobs += 1

        writer = None
        for _ in range(jobs):
            rows = incoming.get()
            if writer is None:
                writer = csv.DictWriter(sys.stdout, fieldnames=rows[0])
                writer.writeheader()
            writer.writerows(rows)
