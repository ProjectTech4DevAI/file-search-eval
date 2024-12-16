import time
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
    latency: float # latency in seconds
    date: str = field(default_factory=lambda: time.strftime('%c'))

    def __str__(self):
        return self.message

@dataclass(frozen=True)
class ResponseJudgement:
    method: str
    score: float
    support: Any
