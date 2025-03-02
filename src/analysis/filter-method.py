import sys
from argparse import ArgumentParser

import pandas as pd

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--method')
    args = arguments.parse_args()

    df = (pd
          .read_csv(sys.stdin)
          .query(f'method == "{args.method}"'))
    df.to_csv(sys.stdout, index=False)
