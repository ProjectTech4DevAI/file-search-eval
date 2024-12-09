#!/bin/bash

ROOT=`git rev-parse --show-toplevel`

export PYTHONPATH=$ROOT

_repetition=3
_src=$ROOT/src/evaluate

while getopts 'g:p:n:h' option; do
    case $option in
	g) _gt="--ground-truth $OPTARG" ;;
	p) _prompts=$OPTARG ;;
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

python $_src/build.py $_gt \
       --repetition $_repetition \
    | python $_src/openai_/run.py $_gt \
	     --user-prompt $_src/openai_/user.txt \
	     --system-prompt $_src/openai_/system.txt \
    | python $_src/deepeval_/run.py $_gt \
	     --user-prompt $_prompts/user \
	     --deep-config $_src/deepeval_/geval.json
