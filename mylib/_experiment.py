import time
from uuid import uuid4
from typing import Any
from pathlib import Path
from dataclasses import dataclass, asdict, field, fields

@dataclass(frozen=True)
class Experiment:
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

    @classmethod
    def stringify(cls, config):
        return ' '.join(str(config.get(x.name)) for x in fields(cls))

@dataclass(frozen=True)
class ExperimentResponse:
    message: str
    model: str
    latency: float # latency in seconds
    response_id: str = field(default_factory=lambda: str(uuid4()))
    date: str = field(default_factory=lambda: time.strftime('%c'))

    def __str__(self):
        return '' if self.message is None else self.message

    def __repr__(self):
        return self.response_id

    def __bool__(self):
        return bool(str(self))

@dataclass(frozen=True)
class ResponseJudgement:
    response_id: str
    method: str
    score: float
    support: Any

class ResponseExtractor:
    def __init__(self, r_id=None):
        self.r_id = r_id

    def __getitem__(self, item):
        for r in reversed(item):
            if self.r_id is None or r['response_id'] == self.r_id:
                return ExperimentResponse(**r)

        raise LookupError(self.r_id)

    def __call__(self, response):
        experiment = self[response]
        if not experiment:
            raise ValueError('NULL response')

        return experiment
