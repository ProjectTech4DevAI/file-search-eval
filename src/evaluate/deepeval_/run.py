import sys
import json
from pathlib import Path
from argparse import ArgumentParser
from dataclasses import asdict
from multiprocessing import Pool, Queue

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

from mylib import (
    Logger,
    Experiment,
    ResponseExtractor,
    ResponseJudgement,
)


#
#
#
class DeepEvaluation:
    _method = 'deepeval:geval'
    _evaluation_params = [
        LLMTestCaseParams.INPUT,
        LLMTestCaseParams.ACTUAL_OUTPUT,
        LLMTestCaseParams.EXPECTED_OUTPUT,
    ]

    def __init__(self, config):
        self.kwargs = json.loads(config.read_text())
        self.kwargs['evaluation_params'] = self._evaluation_params

    def __call__(self, prompt, pr, gt):
        g_eval = GEval(**self.kwargs)
        test = LLMTestCase(
            input=prompt,
            actual_output=pr,
            expected_output=gt,
        )
        g_eval.measure(test, _show_indicator=False)

        return ResponseJudgement(
            repr(pr),
            self._method,
            g_eval.score,
            g_eval.reason,
        )

#
#
#
def func(incoming, outgoing, args):
    evaluator = DeepEvaluation(args.deep_config)
    extractor = ResponseExtractor(args.response_id)

    while True:
        sample = incoming.get()
        config = json.loads(sample)

        user = config['user']
        prompt = args.user_prompt.joinpath(user)
        gt = (args
              .ground_truth
              .joinpath(user, config['reference'])
              .read_text())

        experiment = Experiment.stringify(config)
        try:
            pr = extractor(config['response'])
            judgement = evaluator(prompt, pr, gt)
        except (LookupError, ValueError) as err:
            Logger.error('%s: %s', experiment, err)
            outgoing.put(None)
            continue
        Logger.info(experiment)

        record = config.setdefault('judgement', [])
        record.append(asdict(judgement))

        outgoing.put(config)

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--user-prompt', type=Path)
    arguments.add_argument('--ground-truth', type=Path)
    arguments.add_argument('--deep-config', type=Path)
    arguments.add_argument('--response-id')
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
