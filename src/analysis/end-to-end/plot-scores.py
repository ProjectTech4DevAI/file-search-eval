import sys
from pathlib import Path
from argparse import ArgumentParser

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--output', type=Path)
    args = arguments.parse_args()

    df = pd.read_csv(sys.stdin)
    assert df['method'].nunique() == 1

    ax = sns.barplot(
        x='score',
        y='system',
        hue='docs',
        data=df,
    )

    ax.set_xlabel('Score ({})'.format(df['method'].unique().item()))
    ax.set_ylabel('System prompt')
    ax.set_xlim(0, 1)
    ax.grid(visible=True, axis='x', alpha=0.5, linestyle='dotted')

    ax.legend().remove()
    fig = ax.get_figure()
    fig.legend(loc='outside upper center', fontsize='x-small')

    plt.savefig(args.output, bbox_inches='tight')
