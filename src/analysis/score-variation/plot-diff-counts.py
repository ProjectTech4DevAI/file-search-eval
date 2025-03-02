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
class MethodHandler:
    _method = 'method'

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def titleize(self, ax):
        raise NotImplementedError()

class SingleMethodHandler(MethodHandler):
    def __init__(self, df):
        self.method = df[self._method].unique().item()
        super().__init__(legend=False)

    def	titleize(self, ax):
        ax.set_title(f'Comparison {self._method}: {self.method}')

class MultiMethodHandler(MethodHandler):
    def __init__(self):
        super().__init__(hue=self._method)

    def titleize(self, ax):
        return

#
#
#
if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--output', type=Path)
    args = arguments.parse_args()

    df = pd.read_csv(sys.stdin)
    if df['method'].nunique() == 1:
        handler = SingleMethodHandler(df)
    else:
        handler = MultiMethodHandler()

    ax = sns.countplot(
        x='unique',
        data=df,
        **handler.kwargs,
    )
    ax.grid(visible=True, axis='both', alpha=0.5, linestyle='dotted')
    ax.set_xlabel('Unique scores for same comparison')
    ax.set_ylabel(ax.get_ylabel().title())
    ax.yaxis.set_major_formatter(FuncFormatter(CountPercentage(df)))

    handler.titleize(ax)
    plt.savefig(args.output, bbox_inches='tight')
