import sys
import operator as op
from pathlib import Path
from argparse import ArgumentParser
from dataclasses import dataclass, fields, astuple

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

@dataclass
class GroupKey:
    docs: str
    method: str

    def to_path(self):
        parts = (x.replace('/', '_') for x in astuple(self))
        return Path(*parts)

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--output', type=Path)
    arguments.add_argument('--lowest-score', type=int, default=0)
    arguments.add_argument('--highest-score', type=int, default=1)
    arguments.add_argument('--height-scale', type=float, default=1.5)
    args = arguments.parse_args()

    (x, y) = ('score', 'user')
    components = {
        'y': y,
        'hue': 'system',
    }

    iterable = (
        (op.sub, args.lowest_score),
        (op.add, args.highest_score),
    )
    xlim = [ x(y, 0.1) for (x, y) in iterable ]

    df = pd.read_csv(sys.stdin)
    by = [ x.name for x in fields(GroupKey) ]
    for (i, g) in df.groupby(by, sort=False):
        key = GroupKey(*i)

        output = (args
                  .output
                  .joinpath(key.to_path())
                  .with_suffix('.png'))
        output.parent.mkdir(parents=True, exist_ok=True)

        data = (g
                .groupby(list(components.values()), sort=False)[x]
                .mean()
                .reset_index()
                .sort_values(by=y))

        fig = plt.gcf()
        (width, height) = fig.get_size_inches()
        fig.set_size_inches(width, height * 2)

        sns.stripplot(
            x=x,
            data=data,
            jitter=True,
            **components,
        )

        plt.xlabel(f'Score ({key.method})')
        plt.ylabel('User prompt')
        plt.xlim(*xlim)
        plt.grid(visible=True, axis='both', alpha=0.25, linestyle='dotted')
        plt.legend(title='System prompt')
        plt.title(key.docs)
        plt.axvline(
            x=g[x].mean(),
            color='black',
            linestyle='dashed',
            alpha=0.5,
        )

        plt.savefig(output, bbox_inches='tight')
        plt.close()
