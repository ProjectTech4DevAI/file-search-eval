import sys
import json
from string import Template
from pathlib import Path
from argparse import ArgumentParser
from dataclasses import dataclass, asdict
from multiprocessing import Pool, Queue

from openai import OpenAI
from pydantic import BaseModel

from mylib import Logger, Experiment, ExperimentResponse, ResponseJudgement

#
#
#
@dataclass
class Message:
    role: str
    content: str

#
#
#
class SimilarityEvaluation(BaseModel):
    overlap: str
    difference: str
    details: str
    score: int

#
#
#
class UserMessage:
    def __init__(self, user, gt, low, high):
        self.user = user
        self.gt = gt
        self.kwargs = dict(zip(('lower', 'upper'), (low, high)))

    def __call__(self, config):
        latest = config['response'][-1] # use the most recent response
        response = ExperimentResponse(**latest)
        reference = self.gt.joinpath(config['reference']).read_text()
        content = self.user.substitute(
            response=str(response),
            reference=reference,
            **self.kwargs,
        )

        return Message('user', content)

#
#
#
def func(incoming, outgoing, args):
    client = OpenAI()
    method = f'{args.model}:custom'

    prompt = UserMessage(
        Template(args.user_prompt.read_text()),
        args.ground_truth,
        args.low_score,
        args.high_score,
    )
    system = Message('system', args.system_prompt.read_text())
    messages = [
        asdict(system),
        None,
    ]

    while True:
        sample = incoming.get()

        config = json.loads(sample)
        Logger.info(Experiment.stringify(config))
        messages[-1] = asdict(prompt(config))

        response = client.beta.chat.completions.parse(
            model=args.model,
            messages=messages,
            response_format=SimilarityEvaluation,
        )
        body = (response
                .choices[0]
                .message
                .parsed
                .model_dump())
        score = body.pop('score')
        judgement = ResponseJudgement(method, score, body)

        record = config.setdefault('judgement', [])
        record.append(asdict(judgement))

        outgoing.put(config)

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--user-prompt', type=Path)
    arguments.add_argument('--system-prompt', type=Path)
    arguments.add_argument('--ground-truth', type=Path)
    arguments.add_argument('--low-score', type=int, default=1)
    arguments.add_argument('--high-score', type=int, default=5)
    arguments.add_argument('--model', default='gpt-4o-2024-08-06')
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

        for _ in range(jobs):
            result = incoming.get()
            print(json.dumps(result))
