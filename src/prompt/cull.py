import json
import logging
from pathlib import Path
from argparse import ArgumentParser
from multiprocessing import Pool, JoinableQueue

def func(queue, gt):
    while True:
        experiment = queue.get()
        logging.warning(experiment)

        config = json.loads(experiment.read_text())
        target = gt.joinpath(config['user'])
        if not target.exists():
            logging.error(experiment.name)
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
