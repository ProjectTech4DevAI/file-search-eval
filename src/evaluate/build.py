import sys
import json
import logging
import itertools as it
from string import Template
from pathlib import Path
from argparse import ArgumentParser
from dataclasses import dataclass, asdict
from multiprocessing import Pool, JoinableQueue

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

def func(queue, args):
    prompt = Template(args.user_prompt.read_text())
    system = Message('system', args.system_prompt.read_text())
    refitr = ReferenceIterator(args.repetition)

    while True:
        prediction = queue.get()

        pr = json.loads(prediction.read_text())
        gt = args.ground_truth.joinpath(pr['user'])
        response = pr['response']['message']

        for r in refitr(gt):
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

            out = args.output.joinpath(prediction.name)
            logging.warning(out)
            with out.open('w') as fp:
                print(json.dumps(record, indent=3), file=fp)

        queue.task_done()

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--user-prompt', type=Path)
    arguments.add_argument('--system-prompt', type=Path)
    arguments.add_argument('--ground-truth', type=Path)
    arguments.add_argument('--predictions', type=Path)
    arguments.add_argument('--output', type=Path)
    arguments.add_argument('--repetition', type=int, default=1)
    arguments.add_argument('--low-score', type=int, default=1)
    arguments.add_argument('--high-score', type=int, default=5)
    arguments.add_argument('--workers', type=int)
    args = arguments.parse_args()

    queue = JoinableQueue()
    initargs = (
        queue,
        args,
    )

    with Pool(args.workers, func, initargs):
        for i in args.predictions.iterdir():
            queue.put(i)
        queue.join()
