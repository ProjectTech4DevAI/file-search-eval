import sys
import json
from argparse import ArgumentParser
from multiprocessing import Pool, Queue

from openai import OpenAI
from pydantic import BaseModel
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams

from mylib import Logger, Experiment

@dataclass
class EvaluationResult:
    score: float
    reason: str

class DeepEvaluation:
    _evaluation_params = [
        LLMTestCaseParams.INPUT,
        LLMTestCaseParams.ACTUAL_OUTPUT,
        LLMTestCaseParams.EXPECTED_OUTPUT,
    ],

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.kwargs['evaluation_params'] = self._evaluation_params

    def __call__(self, prompt, pr, gt):
        g_eval = GEval(**self.kwargs)
        test = LLMTestCase(
            input=prompt,
            actual_output=pr,
            expected_output=gt,
        )
        g_eval.measure(test)

        return EvaluationResult(g_eval.score, g_eval.reason)

    @classmethod
    def from_config(cls, config):
        kwargs = json.loads(path.read_text())
        return cls(**kwargs)

def func(incoming, outgoing, args):
    evaluator = DeepEvaluation.from_config(args.deep_config)

    while True:
        sample = incoming.get()
        config = json.loads(sample)
        Logger.info(Experiment.stringify(config))

        user = config['user']
        gt = args.ground_truth.joinpath(user)
        if gt.exists():
            prompt = args.user_prompt.joinpath(user)
            response = config['response']['message'],
            for g in gt.iterdir():
                result = evaluator(prompt, response, g.read_data())
                config['judgement'] = asdict(result)
                outgoing.put(dict(config))

        outgoing.put(None)

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--user-prompt', type=Path)
    arguments.add_argument('--ground-truth', type=Path)
    arguments.add_argument('--deep-config', type=Path)
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
            result = incoming.get()
            if result is None:
                jobs -= 1
            else:
                print(json.dumps(result))
