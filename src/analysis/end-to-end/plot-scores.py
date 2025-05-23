import sys
import functools as ft
from pathlib import Path
from argparse import ArgumentParser
from collections.abc import Iterable

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.ticker import MultipleLocator

from mylib import Logger

@ft.singledispatch
def gather(ax: Axes):
    yield ax

@gather.register
def _(ax: Iterable):
    yield from ax

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--output', type=Path)
    args = arguments.parse_args()

    df = pd.read_csv(sys.stdin)
    methods = df.groupby('method', sort=False)
    hue_order = sorted(df['docs'].unique())

    (fig, axes) = plt.subplots(nrows=methods.ngroups, sharex=True)

    for (i, (ax, (m, g))) in enumerate(zip(gather(axes), methods)):
        Logger.info(m)

        legend = not i
        sns.barplot(
            x='score',
            y='system',
            hue='docs',
            hue_order=hue_order,
            legend=legend,
            data=g,
            ax=ax,
        )

        ax.set_xlabel('Score')
        ax.set_ylabel('System prompt')
        ax.set_xlim(0, 1)
        ax.grid(visible=True, axis='x', alpha=0.5, linestyle='dotted')
        ax.xaxis.set_major_locator(MultipleLocator(base=0.1))
        ax.set_title(
            label=m,
            loc='right',
            fontdict={
                'fontsize': 'small',
                'fontweight': 'bold',
            },
        )

        if legend:
            ax.legend().remove()
            fig = ax.get_figure()
            fig.legend(loc='outside upper center', fontsize='x-small')

    plt.savefig(args.output, bbox_inches='tight')
