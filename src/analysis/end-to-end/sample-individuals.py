import sys
import csv
import string
from argparse import ArgumentParser
from dataclasses import dataclass, astuple, fields
from multiprocessing import Pool, Queue

import pandas as pd

from mylib import Logger

@dataclass(frozen=True)
class GroupKey:
    docs: str
    system: str

    def __str__(self):
        return ' '.join(astuple(self))

def func(incoming, outgoing, args):
    assert args.samples <= len(string.ascii_uppercase)
    letters = string.ascii_uppercase[:args.samples]

    while True:
        (group, df) = incoming.get()
        Logger.info(group)

        for l in letters:
            if args.seed is not None:
                args.seed += 1
            records = (df
                       .sample(frac=1, random_state=args.seed)
                       .drop_duplicates(subset='user')
                       .assign(sample=l)
                       .to_dict(orient='records'))
            outgoing.put(records)
        outgoing.put(None)

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--samples', type=int, default=1)
    arguments.add_argument('--seed', type=int)
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
        by = [ x.name for x in fields(GroupKey) ]
        df = pd.read_csv(sys.stdin)
        jobs = 0
        for (i, g) in df.groupby(by, sort=False):
            key = GroupKey(*i)
            outgoing.put((key, g))
            jobs += 1

        writer = None
        while jobs:
            rows = incoming.get()
            if rows is None:
                jobs -= 1
            else:
                if writer is None:
                    writer = csv.DictWriter(sys.stdout, fieldnames=rows[0])
                    writer.writeheader()
                writer.writerows(rows)
