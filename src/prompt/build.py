import json
import itertools as it
from pathlib import Path
from argparse import ArgumentParser
from dataclasses import dataclass, asdict

from mylib import Logger

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

def documents(path):
    for root in path.iterdir():
        for i in root.iterdir():
            yield i.relative_to(path)

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--model', action='append')
    arguments.add_argument('--user-prompts', type=Path)
    arguments.add_argument('--system-prompts', type=Path)
    arguments.add_argument('--documents', type=Path)
    arguments.add_argument('--repetition', type=int, default=1)
    args = arguments.parse_args()

    conditions = (
        args.model,
        args.system_prompts.iterdir(),
        args.user_prompts.iterdir(),
        documents(args.documents),
        range(args.repetition),
    )
    for i in it.product(*conditions):
        e = Experiment(*i)
        Logger.info(e)
        print(json.dumps(dict(e)))
