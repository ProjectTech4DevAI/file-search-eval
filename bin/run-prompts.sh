#!/bin/bash

ROOT=`git rev-parse --show-toplevel`

_repetition=5
_prompts=$ROOT/prompts
_models=(
    gpt-4o-mini
)

while getopts 'o:n:c:h' option; do
    case $option in
        o) _output=$OPTARG ;;
	n) _repetition=$OPTARG ;;
	c) _cull=1 ;;
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
e_out=$_output/experiments
mkdir --parents $e_out

models=`sed -e's/ / --model /g' <<< ${_models[@]}`
_git=`git rev-parse HEAD`

python $ROOT/src/prompt/build.py \
       --model $models \
       --user-prompts $_prompts/user \
       --system-prompts $_prompts/system \
       --documents $ROOT/docs \
       --repetition $_repetition \
       --extra-info git:$_git \
       --output $e_out

if [ $_cull ]; then
    python $ROOT/src/prompt/cull.py \
	   --experiments $e_out \
	   --ground-truth $ROOT/golden
done

#
#
#
r_out=$_output/results
mkdir --parents	$r_out

for i in $e_out/*; do
    out=$r_out/`basename $i`
    cat <<EOF
python $ROOT/src/prompt/run.py \
    --document-root $ROOT/docs \
    --prompt-root $_prompts < $i > $out
EOF
done | parallel --will-cite --line-buffer --delay 4
