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
    args = arguments.parse_args()

    #
    #
    #
    xlabel = '' if args.model is None else args.model + ' '

    #
    #
    #
    df = pd.read_csv(sys.stdin)

    #
    #
    #
    sns.barplot(
        x='score',
        y='system',
        data=df,
        errorbar=('pi', 50),
    )

    plt.xlabel(f'{xlabel}score')
    plt.ylabel('System prompt')
    plt.xlim(args.lowest_score, args.highest_score)
    plt.grid(visible=True, axis='x', alpha=0.5, linestyle='dotted')

    plt.savefig(args.output, bbox_inches='tight')
