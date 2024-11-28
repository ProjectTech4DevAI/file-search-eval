import json
import logging
import itertools as it
from pathlib import Path
from argparse import ArgumentParser
from tempfile import NamedTemporaryFile
from dataclasses import dataclass, asdict
from multiprocessing import Pool, JoinableQueue

@dataclass
class Experiment:
    model: str
    system: Path
    user: Path
    docs: Path
    sequence: int

    def __iter__(self):
        values = asdict(self)
        for (k, v) in values.items():
            if k in ('system', 'user'):
                v = v.name
            elif k == 'docs':
                v = str(v)

            yield (k, v)

def func(queue, args):
    kwargs = dict(x.split(':') for x in args.extra_info)

    while True:
        experiment = queue.get()
        logging.warning(experiment)

        config = dict(kwargs)
        config.update(experiment)
        with NamedTemporaryFile(mode='w',
                                suffix='.json',
                                prefix='',
                                delete=False,
                                dir=args.output) as fp:
            print(json.dumps(config, indent=3), file=fp)

        queue.task_done()

def documents(path):
    for root in path.iterdir():
        for i in root.iterdir():
            yield i.relative_to(path)

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--model', action='append')
    arguments.add_argument('--extra-info', action='append')
    arguments.add_argument('--user-prompts', type=Path)
    arguments.add_argument('--system-prompts', type=Path)
    arguments.add_argument('--documents', type=Path)
    arguments.add_argument('--repetition', type=int, default=1)
    arguments.add_argument('--output', type=Path)
    arguments.add_argument('--workers', type=int)
    args = arguments.parse_args()

    queue = JoinableQueue()
    initargs = (
        queue,
        args,
    )

    with Pool(args.workers, func, initargs) as pool:
        conditions = (
            args.model,
            args.system_prompts.iterdir(),
            args.user_prompts.iterdir(),
            documents(args.documents),
            range(args.repetition),
        )
        for i in it.product(*conditions):
            queue.put(Experiment(*i))
        queue.join()
