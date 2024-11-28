#!/bin/bash

ROOT=`git rev-parse --show-toplevel`

_repetition=3
_prompts=$ROOT/prompts

while getopts 'i:o:n:g:h' option; do
    case $option in
	i) _input=$OPTARG ;;
        o) _output=$OPTARG ;;
	g) _gt=$OPTARG ;;
	n) _repetition=$OPTARG ;;
        h)
            cat <<EOF
Usage: $0
 -i Directory containing LLM responses
 -o Directory to deposit experiments and results
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

#
#
#
e_out=$_output/experiments
mkdir --parents $e_out

python $ROOT/src/evaluate/build.py \
       --user-prompt $_prompts/evaluate/user \
       --system-prompt $_prompts/evaluate/system \
       --ground-truth $_gt \
       --repetition $_repetition \
       --predictions $_input \
       --output $e_out

#
#
#
r_out=$_output/results
mkdir --parents	$r_out

for i in $e_out/*; do
    out=$r_out/`basename $i`
    cat <<EOF
python $ROOT/src/evaluate/run.py < $i > $out
EOF
done | parallel --will-cite --line-buffer --delay 4
