import sys
from pathlib import Path
from argparse import ArgumentParser

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--model')
    arguments.add_argument('--output', type=Path)
    arguments.add_argument('--lowest-score', type=int, default=1)
    arguments.add_argument('--highest-score', type=int, default=10)
    arguments.add_argument('--height-scale', type=float, default=1.5)
    args = arguments.parse_args()

    #
    #
    #
    x = 'score'
    components = {
        'y': 'user',
        'hue': 'system',
    }
    xlabel = '' if args.model is None else args.model + ' '

    #
    #
    #
    df = (pd
          .read_csv(sys.stdin)
          .groupby(list(components.values()), sort=False)[x]
          .mean()
          .reset_index())

    #
    #
    #
    fig = plt.gcf()
    (width, height) = fig.get_size_inches()
    fig.set_size_inches(width, height * 2)

    sns.stripplot(
        x=x,
        data=df,
        jitter=True,
        **components,
    )

    plt.xlabel(f'{xlabel}score')
    plt.ylabel('User prompt')
    plt.xlim(args.lowest_score - 1, args.highest_score + 1)
    plt.grid(visible=True, axis='both', alpha=0.25, linestyle='dotted')

    plt.savefig(args.output, bbox_inches='tight')
