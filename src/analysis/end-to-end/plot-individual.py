import sys
from pathlib import Path
from argparse import ArgumentParser
from multiprocessing import Pool, JoinableQueue

import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from mylib import Logger

def func(queue, args):
    while True:
        (system, df) = queue.get()
        Logger.info(system)

        ax = sns.barplot(
            x='score',
            y='sample',
            hue='docs',
            errorbar=None,
            data=df,
        )

        ax.set_xlabel('Score ({})'.format(df['method'].unique().item()))
        ax.set_ylabel(f'Sample run (system prompt {system})')
        ax.set_xlim(0, 1)
        ax.grid(visible=True, axis='x', alpha=0.5, linestyle='dotted')

        ax.legend().remove()
        fig = ax.get_figure()
        fig.legend(loc='outside upper center', fontsize='x-small')

        output = (args
                  .output_directory
                  .joinpath(system)
                  .with_suffix('.png'))
        plt.savefig(output, bbox_inches='tight')
        plt.close()

        queue.task_done()

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--output-directory', type=Path)
    arguments.add_argument('--workers', type=int)
    args = arguments.parse_args()

    queue = JoinableQueue()
    initargs = (
        queue,
        args,
    )

    with Pool(args.workers, func, initargs):
        df = pd.read_csv(sys.stdin)
        assert df['method'].nunique() == 1
        groups = df.groupby('system', sort=False)

        for i in groups:
            queue.put(i)
        queue.join()
