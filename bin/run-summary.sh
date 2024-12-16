#!/bin/bash

ROOT=`git rev-parse --show-toplevel`

export PYTHONPATH=$ROOT

_src=$ROOT/src/refine/summarize
python $_src/run.py --system-prompt $_src/system.txt
