import json
import itertools as it
from pathlib import Path
from argparse import ArgumentParser
from dataclasses import fields

from mylib import Logger, Experiment

def documents(path):
    for root in path.iterdir():
        for i in root.iterdir():
            yield i.relative_to(path)

def exclusions(paths):
    keys = (x.name for x in fields(Experiment))
    for p in paths:
        with p.open() as fp:
            for line in fp:
                sample = json.loads(line)
                yield Experiment(**{ x: sample[x] for x in keys })

def experiments(args):
    conditions = (
        args.system_prompts.iterdir(),
        args.user_prompts.iterdir(),
        documents(args.documents),
        range(args.repetition),
    )

    yield from it.starmap(Experiment, it.product(*conditions))

#
#
#
if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--user-prompts', type=Path)
    arguments.add_argument('--system-prompts', type=Path)
    arguments.add_argument('--documents', type=Path)
    arguments.add_argument('--exclude', type=Path, action='append')
    arguments.add_argument('--extra-info', action='append')
    arguments.add_argument('--repetition', type=int, default=1)
    args = arguments.parse_args()

    extra = dict(x.split(':') for x in args.extra_info)
    ignore = set(exclusions(args.exclude))

    for e in experiments(args):
        if e in ignore:
            Logger.error(e)
            continue

        Logger.info(e)
        config = dict(extra)
        config.update(e)

        print(json.dumps(config))
