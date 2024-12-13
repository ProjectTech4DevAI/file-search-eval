import json
import itertools as it
from pathlib import Path
from argparse import ArgumentParser

from mylib import Logger, Experiment

def documents(path):
    for root in path.iterdir():
        for i in root.iterdir():
            yield i.relative_to(path)

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--user-prompts', type=Path)
    arguments.add_argument('--system-prompts', type=Path)
    arguments.add_argument('--documents', type=Path)
    arguments.add_argument('--extra-info', action='append')
    arguments.add_argument('--repetition', type=int, default=1)
    args = arguments.parse_args()

    conditions = (
        args.system_prompts.iterdir(),
        args.user_prompts.iterdir(),
        documents(args.documents),
        range(args.repetition),
    )
    extra = dict(x.split(':') for x in args.extra_info)

    for i in it.product(*conditions):
        e = Experiment(*i)
        Logger.info(e)

        Logger.info(e)
        config = dict(extra)
        config.update(e)

        print(json.dumps(config))
