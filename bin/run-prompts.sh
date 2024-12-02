#!/bin/bash

ROOT=`git rev-parse --show-toplevel`

export PYTHONPATH=$ROOT

_repetition=5
_default_model=gpt-4o-mini

while getopts 'o:n:p:d:g:m:ch' option; do
    case $option in
        o) _output=$OPTARG ;;
	n) _repetition=$OPTARG ;;
	p) _prompts=$OPTARG ;;
	d) _documents=$OPTARG ;;
	g) _gt=$OPTARG ;;
	m) _models=( ${_models[@]} $OPTARG ) ;;
        h)
            cat <<EOF
Usage: $0
 -o Directory to deposit experiments and results
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

if [ ! $_models ]; then
    _models=( $_default_model )
fi

#
#
#
e_out=$_output/experiments
mkdir --parents $e_out

models=`sed -e's/ / --model /g' <<< ${_models[@]}`
_git=`git rev-parse HEAD`

python $ROOT/src/prompt/build.py \
       --model $models \
       --user-prompts $_prompts/user \
       --system-prompts $_prompts/system \
       --documents $_documents \
       --repetition $_repetition \
       --extra-info git:$_git \
       --output $e_out

if [ $_gt ]; then
    python $ROOT/src/prompt/cull.py \
	   --experiments $e_out \
	   --ground-truth $_gt
fi

#
#
#
r_out=$_output/results
mkdir --parents	$r_out

for i in $e_out/*; do
    out=$r_out/`basename $i`
    cat <<EOF
python $ROOT/src/prompt/run.py \
    --document-root $_documents \
    --prompt-root $_prompts < $i > $out
EOF
done | parallel --will-cite --line-buffer --delay 4
