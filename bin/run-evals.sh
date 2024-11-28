#!/bin/bash

ROOT=`git rev-parse --show-toplevel`

_repetition=3
_prompts=$ROOT/prompts

while getopts 'i:o:n:h' option; do
    case $option in
	i) _input=$OPTARG ;;
        o) _output=$OPTARG ;;
        h)
            cat <<EOF
Usage: $0
 -o Output directory
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
e_out=$_output/evals
mkdir --parents $e_out

python $ROOT/src/evaluate/build.py \
       --user-prompt $_prompts/evaluate/user \
       --system-prompt $_prompts/evaluate/system \
       --ground-truth $ROOT/golden \
       --repetition $_repetition \
       --predictions $_input \
       --output $e_out

#
#
#
r_out=$_output/compares
mkdir --parents	$r_out

for i in $e_out/*; do
    out=$r_out/`basename $i`
    cat <<EOF
python $ROOT/src/evaluate/run.py < $i > $out
EOF
done | parallel --will-cite --line-buffer --delay 4
