import json
import itertools as it
import functools as ft
from pathlib import Path
from argparse import ArgumentParser
from dataclasses import fields

from mylib import Logger, Experiment

def documents(path):
    for root in path.iterdir():
        for i in root.iterdir():
            yield i.relative_to(path)

def experiments(args):
    conditions = (
        args.system_prompts.iterdir(),
        args.user_prompts.iterdir(),
        documents(args.documents),
        range(args.repetition),
    )

    yield from it.starmap(Experiment, it.product(*conditions))

class Excluder:
    @staticmethod
    def extract(paths):
        keys = (x.name for x in fields(Experiment))
        for p in paths:
            with p.open() as fp:
                for line in fp:
                    sample = json.loads(line)
                    kwargs = { x: sample[x] for x in keys }
                    yield Experiment(**kwargs)

    def __init__(self, exclusions):
        self.exclusions = set()
        if exclusions:
            self.exclusions.update(self.extract(exclusions))

    @ft.singledispatchmethod
    def __contains__(self, item):
        raise TypeError(type(item))

    @__contains__.register
    def _(self, item: dict):
        e = Experiment(**item)
        return e in self.exclusions

    @__contains__.register
    def _(self, item: Experiment):
        return dict(item) in self

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
    ignore = Excluder(args.exclude)

    for e in experiments(args):
        if e in ignore:
            Logger.error(e)
            continue

        Logger.info(e)
        config = dict(extra)
        config.update(e)

        print(json.dumps(config))
