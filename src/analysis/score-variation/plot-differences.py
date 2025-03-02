import sys
import csv
import json
from pathlib import Path
from argparse import ArgumentParser

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

#
#
#
class CountPercentage:
    def __init__(self, df):
        self.n = len(df)

    def __call__(self, x, pos):
        return '{:.0f} ({:.0%})'.format(x, x / self.n)

#
#
#
if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--scale', type=int)
    arguments.add_argument('--output', type=Path)
    args = arguments.parse_args()

    df = pd.read_csv(sys.stdin)
    x = df['difference']
    if args.scale:
        x *= args.scale
    assert df['method'].nunique() == 1

    ax = sns.countplot(
        x=x,
        data=df,
        legend=False,
    )
    ax.grid(visible=True, axis='both', alpha=0.5, linestyle='dotted')
    ax.set_xlabel('Score range for same comparison')
    # ax.set_ylabel(ax.get_ylabel().title())
    ax.yaxis.set_major_formatter(FuncFormatter(CountPercentage(df)))

    plt.savefig(args.output, bbox_inches='tight')
