#!/bin/bash

ROOT=`git rev-parse --show-toplevel`

export PYTHONPATH=$ROOT

_repetition=5
_default_model=gpt-4o-mini

while getopts 'n:p:d:g:m:e:ch' option; do
    case $option in
	n) _repetition=$OPTARG ;;
	p) _prompts=$OPTARG ;;
	d) _documents=$OPTARG ;;
	g) _gt=$OPTARG ;;
	m) _models=( ${_models[@]} --model $OPTARG ) ;;
	e) _extra=( ${_extra[@]} --extra-info $OPTARG ) ;;
        h)
            cat <<EOF
Usage: $0
 -n Number of times to repeat each judgement (default $_repetition)
 -p Directory containing system and user prompts. The value provided
    is expected to contain "system" and "user" subdirectories
 -d Directory containing documents for the OpenAI vector store
 -g Directory containing reference responses. If this option is
    provided only user prompts that have a corresponding
    ground truth answer will be run
 -m OpenAI model. Specify multiple times to test multiple models
EOF
            exit 0
            ;;
        *)
            echo -e Unrecognized option \"$option\"
            exit 1
            ;;
    esac
done

if [ ${#_models[@]} -eq 0 ]; then
    _models=( --model $_default_model )
fi

python $ROOT/src/prompt/build.py ${_extra[@]} \
       --user-prompts $_prompts/user \
       --system-prompts $_prompts/system \
       --documents $_documents \
       --repetition $_repetition | \
    if [ $_gt ]; then
	python $ROOT/src/prompt/cull.py --ground-truth $_gt
    else
	cat
    fi | \
	python $ROOT/src/prompt/run.py ${_models[@]} \
	       --document-root $_documents \
	       --prompt-root $_prompts
