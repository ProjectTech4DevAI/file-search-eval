import sys
import json
import logging
from argparse import ArgumentParser

from openai import OpenAI
from pydantic import BaseModel

class SimilarityEvaluation(BaseModel):
    overlap: str
    difference: str
    details: str
    score: int

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--model', default='gpt-4o-2024-08-06')
    args = arguments.parse_args()

    config = json.loads(sys.stdin.read())
    if logging.getLogger().isEnabledFor(logging.CRITICAL):
        keys = (
            'system',
            'user',
            'sequence',
            'comparison',
        )
        message = ' '.join(str(config.get(x)) for x in keys)
        logging.critical(message)

    client = OpenAI()
    response = client.beta.chat.completions.parse(
        model=args.model,
        messages=config['evaluation'],
        response_format=SimilarityEvaluation,
    )
    config['judgement'] = response.choices[0].message.parsed.dict()

    print(json.dumps(config, indent=3))
