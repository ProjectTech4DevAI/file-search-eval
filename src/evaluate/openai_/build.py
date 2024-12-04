import sys
import json
import itertools as it
from string import Template
from pathlib import Path
from argparse import ArgumentParser
from dataclasses import dataclass, asdict
from multiprocessing import Pool, Queue

# from mylib import Logger

@dataclass
class Message:
    role: str
    content: str

class ReferenceIterator:
    @dataclass
    class Reference:
        seq: int
        data: Path

    def __init__(self, n):
        self.n = n

    def __call__(self, gt):
        iterable = it.product(range(self.n), gt.iterdir())
        yield from it.starmap(self.Reference, iterable)

def func(incoming, outgoing, args):
    prompt = Template(args.user_prompt.read_text())
    system = Message('system', args.system_prompt.read_text())
    references = ReferenceIterator(args.repetition)

    while True:
        response = incoming.get()

        pr = json.loads(response)
        gt = args.ground_truth.joinpath(pr['user'])
        if gt.exists():
            response = pr['response']['message']

            for r in references(gt):
                reference = r.data.read_text()
                content = prompt.substitute(
                    response=response,
                    reference=reference,
                    lower=args.low_score,
                    upper=args.high_score,
                )
                user = Message('user', content)

                record = dict(pr)
                record.update({
                    'comparison': r.seq,
                    'reference': r.data.name,
                    'evaluation': list(map(asdict, (system, user))),
                })
                outgoing.put(record)
        outgoing.put(None)

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--user-prompt', type=Path)
    arguments.add_argument('--system-prompt', type=Path)
    arguments.add_argument('--ground-truth', type=Path)
    arguments.add_argument('--repetition', type=int, default=1)
    arguments.add_argument('--low-score', type=int, default=1)
    arguments.add_argument('--high-score', type=int, default=5)
    arguments.add_argument('--workers', type=int)
    args = arguments.parse_args()

    incoming = Queue()
    outgoing = Queue()
    initargs = (
        outgoing,
        incoming,
        args,
    )

    with Pool(args.workers, func, initargs):
        jobs = 0
        for i in sys.stdin:
            outgoing.put(i)
            jobs += 1

        while jobs:
            record = incoming.get()
            if record is None:
                jobs -= 1
            else:
                print(json.dumps(record))
