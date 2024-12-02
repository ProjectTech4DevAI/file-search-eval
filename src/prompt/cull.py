import json
from pathlib import Path
from argparse import ArgumentParser
from multiprocessing import Pool, JoinableQueue

from mylib import Logger

def func(queue, gt):
    while True:
        experiment = queue.get()
        Logger.info(experiment)

        config = json.loads(experiment.read_text())
        target = gt.joinpath(config['user'])
        if not target.exists():
            Logger.warning('No ground truth: %s', experiment.name)
            experiment.unlink()

        queue.task_done()

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--experiments', type=Path)
    arguments.add_argument('--ground-truth', type=Path)
    arguments.add_argument('--workers', type=int)
    args = arguments.parse_args()

    queue = JoinableQueue()
    initargs = (
        queue,
        args.ground_truth,
    )

    with Pool(args.workers, func, initargs):
        for i in args.experiments.iterdir():
            queue.put(i)
        queue.join()
