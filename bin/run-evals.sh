#!/bin/bash

ROOT=`git rev-parse --show-toplevel`

export PYTHONPATH=$ROOT

_repetition=3
_prompts=$ROOT/docs/prompts/openai
_src=$ROOT/src/evaluate/openai_

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

python $_src/build.py \
       --user-prompt $_prompts/user \
       --system-prompt $_prompts/system \
       --ground-truth $_gt \
       --repetition $_repetition \
    | python $_src/run.py
