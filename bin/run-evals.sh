#!/bin/bash

ROOT=`git rev-parse --show-toplevel`

export PYTHONPATH=$ROOT

_repetition=3
_prompts=$ROOT/docs/prompts

while getopts 'n:g:h' option; do
    case $option in
	g) _gt=$OPTARG ;;
	n) _repetition=$OPTARG ;;
        h)
            cat <<EOF
Usage: $0
 -g Directory containing reference responses
 -n Number of times to repeat each judgement (default $_repetition)
EOF
            exit 0
            ;;
        *)
            echo -e Unrecognized option \"$option\"
            exit 1
            ;;
    esac
done

python $ROOT/src/evaluate/_openai/build.py \
       --user-prompt $_prompts/evaluate/user \
       --system-prompt $_prompts/evaluate/system \
       --ground-truth $_gt \
       --repetition $_repetition \
    | python $ROOT/src/evaluate/run.py
