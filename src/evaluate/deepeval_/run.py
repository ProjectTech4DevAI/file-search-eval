import sys
import json
from pathlib import Path
from argparse import ArgumentParser
from dataclasses import asdict, replace
from multiprocessing import Pool, Queue

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

from mylib import Logger, Experiment, ExperimentResponse, ResponseJudgement

#
#
#
class DeepEvaluation:
    _evaluation_params = [
        LLMTestCaseParams.INPUT,
        LLMTestCaseParams.ACTUAL_OUTPUT,
        LLMTestCaseParams.EXPECTED_OUTPUT,
    ]

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.kwargs['evaluation_params'] = self._evaluation_params

    def __call__(self, prompt, pr, gt):
        if not pr:
            raise ValueError('NULL response')
        g_eval = GEval(**self.kwargs)
        test = LLMTestCase(
            input=prompt,
            actual_output=pr,
            expected_output=gt,
        )
        g_eval.measure(test, _show_indicator=False)

        return ResponseJudgement(None, g_eval.score, g_eval.reason)

    @classmethod
    def from_config(cls, config):
        kwargs = json.loads(config.read_text())
        return cls(**kwargs)

#
#
#
def func(incoming, outgoing, args):
    _method = 'deepeval:geval'
    evaluator = DeepEvaluation.from_config(args.deep_config)

    while True:
        sample = incoming.get()

        config = json.loads(sample)
        c_string = Experiment.stringify(config)
        Logger.info(c_string)
        user = config['user']

        prompt = args.user_prompt.joinpath(user)
        gt = (args
              .ground_truth
              .joinpath(user, config['reference'])
              .read_text())
        kwargs = config['response'][args.response_index]
        pr = ExperimentResponse(**kwargs)

        try:
            judgement = evaluator(prompt, pr, gt)
        except ValueError as err:
            Logger.error('%s: %s', c_string, err)
            outgoing.put(None)
            continue

        judgement = replace(judgement, method=_method)

        record = config.setdefault('judgement', [])
        record.append(asdict(judgement))

        outgoing.put(config)

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--user-prompt', type=Path)
    arguments.add_argument('--ground-truth', type=Path)
    arguments.add_argument('--deep-config', type=Path)
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
            if result is not None:
                print(json.dumps(result))
