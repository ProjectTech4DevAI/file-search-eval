import sys
import csv
from argparse import ArgumentParser
from dataclasses import dataclass, astuple, asdict, fields
from multiprocessing import Pool

import pandas as pd

from mylib import Logger

@dataclass(frozen=True)
class GroupKey:
    system: str
    user: str
    docs: str
    sequence: int
    method: str

    def __str__(self):
        return ', '.join(map(str, astuple(self)))

@dataclass(frozen=True)
class Record:
    method: str
    unique: int
    difference: int

#
#
#
def attrs(cls):
    yield from (x.name for x in fields(cls))

def func(args):
    (key, df) = args
    Logger.info(key)

    score = df['score']
    unique = score.nunique()
    difference = score.max() - score.min()

    return Record(key.method, unique, difference)

def scanf(fp):
    df = pd.read_csv(fp)
    for (i, g) in df.groupby(list(attrs(GroupKey)), sort=False):
        key = GroupKey(*i)
        yield (key, g)

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--workers', type=int)
    args = arguments.parse_args()

    with Pool(args.workers) as pool:
        writer = csv.DictWriter(sys.stdout, fieldnames=list(attrs(Record)))
        writer.writeheader()
        for i in pool.imap_unordered(func, scanf(sys.stdin)):
            writer.writerow(asdict(i))
