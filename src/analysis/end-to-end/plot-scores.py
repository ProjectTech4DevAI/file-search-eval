import sys
from pathlib import Path
from argparse import ArgumentParser

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter, MultipleLocator

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--output', type=Path)
    arguments.add_argument('--lowest-score', type=int, default=0)
    arguments.add_argument('--highest-score', type=int, default=1)
    args = arguments.parse_args()

    docs = 'docs'
    df = pd.read_csv(sys.stdin)
    hue_order = sorted(df[docs].unique())

    groups = df.groupby('method', sort=False)
    (fig, axes) = plt.subplots(
        nrows=groups.ngroups,
        # sharex=True,
        gridspec_kw={
            'hspace': 0.4,
        },
    )

    for (i, (ax, (m, g))) in enumerate(zip(axes, groups), 1):
        sns.barplot(
            x='score',
            y='system',
            hue=docs,
            hue_order=hue_order,
            data=g,
            ax=ax,
        )

        ax.set_xlabel(f'Score ({m})')
        ax.set_ylabel('System prompt')
        ax.set_xlim(args.lowest_score, args.highest_score)
        ax.grid(visible=True, axis='x', alpha=0.5, linestyle='dotted')
        ax.legend().remove()
        ax.xaxis.set_major_locator(MultipleLocator(base=0.1))
        if i == 1:
            fig.legend(loc='outside upper center')
        if i < groups.ngroups:
            ax.xaxis.set_major_formatter(NullFormatter())

    plt.savefig(args.output, bbox_inches='tight')
