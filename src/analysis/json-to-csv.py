import sys
import csv
import json
import logging
import functools as ft
from typing import Union
from pathlib import Path
from argparse import ArgumentParser
from multiprocessing import Pool

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
    logging.warning(args)
    data = json.loads(args.read_text())
    score = data['judgement']['score']

    return dict(parse(data), score=score)

#
#
#
if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--comparisons', type=Path)
    arguments.add_argument('--workers', type=int)
    args = arguments.parse_args()

    with Pool(args.workers) as pool:
        writer = None
        iterable = args.comparisons.iterdir()
        for i in pool.imap_unordered(func, iterable):
            if writer is None:
                writer = csv.DictWriter(sys.stdout, fieldnames=i)
                writer.writeheader()
            writer.writerow(i)
