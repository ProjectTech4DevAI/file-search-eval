import sys
import time
import json
from pathlib import Path
from argparse import ArgumentParser
from multiprocessing import Pool, Queue

from openai import OpenAI

from mylib import Logger, ExperimentResponse

def func(incoming, outgoing, args):
    client = OpenAI()
    system = args.system_prompt.read_text()

    while True:
        sample = incoming.get()
        config = json.loads(sample)
        Logger.info(Experiment.stringify(config))

        view = config['response'][args.response_index]
        experiment = ExperimentResponse(**view)

        iterable = zip(('system', 'user'), (system, str(experiment)))
        messages = [ { 'role': x, 'content': y } for (x, y) in iterable ]

        t_start = time.perf_counter()
        response = client.chat.completions.create(
            model=config['model'],
            messages=messages,
        )
        t_end = time.perf_counter()

        message = response.choices[0].message.content
        result = ExperimentResponse(message, t_end - t_start)
        view.append(asdict(result))

        outgoing.put(config)

if __name__ == '__main__':
    arguments = ArgumentParser()
    # arguments.add_argument('--user-prompt', type=Path)
    arguments.add_argument('--system-prompt', type=Path)
    arguments.add_argument('--response-index', type=int, default=-1)
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
