import sys
import csv
import json
import functools as ft
from typing import Union
from pathlib import Path
from argparse import ArgumentParser
from multiprocessing import Pool

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

def func(args):
    # Logger.info(args)
    data = json.loads(args)
    score = data['judgement']['score']

    return dict(parse(data), score=score)

#
#
#
if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--workers', type=int)
    args = arguments.parse_args()

    with Pool(args.workers) as pool:
        writer = None
        for i in pool.imap_unordered(func, sys.stdin):
            if writer is None:
                writer = csv.DictWriter(sys.stdout, fieldnames=i)
                writer.writeheader()
            writer.writerow(i)
