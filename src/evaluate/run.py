import sys
import json
from argparse import ArgumentParser
from multiprocessing import Pool, Queue

from openai import OpenAI
from pydantic import BaseModel

# from mylib import Logger

class SimilarityEvaluation(BaseModel):
    overlap: str
    difference: str
    details: str
    score: int

def func(incoming, outgoing, args):
    client = OpenAI()

    while True:
        sample = incoming.get()
        config = json.loads(sample)

        response = client.beta.chat.completions.parse(
            model=args.model,
            messages=config['evaluation'],
            response_format=SimilarityEvaluation,
        )
        config['judgement'] = (response
                               .choices[0]
                               .message
                               .parsed.model_dump())

        outgoing.put(config)

if __name__ == '__main__':
    arguments = ArgumentParser()
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
