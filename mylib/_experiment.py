from pathlib import Path
from dataclasses import dataclass, asdict, fields

@dataclass
class Experiment:
    model: str
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
