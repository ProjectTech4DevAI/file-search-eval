# Document Supported LLM Evaluation

This repository automates OpenAI File Search testing.

## Setup

### Environment

1. Ensure your OpenAI key is in the environment

   ```bash
   export OPENAI_API_KEY=...
   ```

2. Ensure you have a proper Python environment. Your Python version
   should be 3.10 or above. If you do not have the packages required
   in your default environment, consider creating a virtual one:

   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Update your Python path

   ```bash
   export PYTHONPATH=`git rev-parse --show-toplevel`:$PYTHONPATH
   ```

4. (Optional) Set the Python log level:

   ```bash
   export PYTHONLOGLEVEL=info
   ```

   The default level is "warning", however most of the scripts produce
   useful information at "info". Valid values come from the [Python
   logging
   module](https://docs.python.org/3/library/logging.html#logging-levels).

### Prompts and documents

#### Prompts

Gather the prompts and documents that will supply the tests. User and
system prompts are expected to live under a common directory:

```
/data/prompts/
├── system
│   ├── system-file-1
│   ├── system-file-2
│   ├── ...
│   └── system-file-n
└── user
    ├── user-file-1
    ├── user-file-2
    ├── ...
    └── user-file-n
```

#### Vector store documents

Documents that support LLM interaction -- files that go into the
vector store -- are expected to obey the following structure:

```
/data/documents
├── method_1
│   └── instance_1
│       └── ...
├── method_2
│   └── instance_1
│       └── ...
```

Where the actual documents live within the `...` sub-level. Each
parent folder, `method_n/instance_n` is designed to hold a different
version of the document sets.

#### Ground truth responses

Responses that are deemed to be "correct" should be stored as follows:

```
/data/ground-truth
├── user-file-1
│   ├── file-1
│   ├── file-2
│   ├── ...
│   └── file-n
└── user-file-2
    ├── file-1
    ├── file-2
    ├── ...
    └── file-n
```

Where `user-file-n` is the basename of the user prompt, and `file-n`
is an arbitrary file name. It is imperative that the `user-file-n`
names be present in `/data/prompts/user`. More formally

```bash
$(for i in /data/ground-truth/*; do test -e /data/prompts/`basename $i` || exit 1; done); echo $?
```

should print 0 if things are correct, 1 otherwise.

## Run

There are two components to this repository: getting responses to
queries, and evaluating those responses.

### Get responses to queries

The prompt phase takes each combination of

* system prompt
* user prompt
* markdown docs
* OpenAI models

and generates completions from OpenAI File Search that are supported
by the markdown files. By default, each user prompt is sent multiple
times to test consistency.

Response generation happens in two phases. In the first "experiments"
are created specifying the system prompt, user prompt, markdown files,
and user prompt iteration being tested. In the second phase each
experiment file is used to setup a File Search interaction, including
a vector store, assistant, thread, and message. The OpenAI resources
are deleted once the query has completed.

The entire process can be run from `bin/run-prompts.sh` as
follows. Assuming your environment is setup:

```bash
./bin/run-prompts.sh -p /data/prompts -d /data/documents > responses.jsonl
```

This will produce `responses.jsonl`, a JSONL file detailing each
prompt and the LLM's response. See `./bin/run-prompts.sh -h` for
documentation and other options, and to get a sense for which Python
scripts within this repository are doing the work.

#### When not all user prompts have ground truth

One option to keep in mind is `-g`, which points the response
generator at your ground truth directory:

```bash
./bin/run-prompts.sh ... -g /data/ground-truth ...
```

Providing this option steers the generator to only consider prompts
that have corresponding ground truth. User prompts that do not have
ground truth are ignored and will not have a response in the
output. Providing this option can help to make response generation
more efficient in cases where the ratio of ground truth to user
prompts is low, and the primary objective is evaluation.

The evaluation phase gracefully ignores responses without ground
truth, so the decision to use `-g` is purely about response generation
efficiency.

### Obtain LLM judgements to responses

Once responses have been generated, they can be judged using an
LLM. This process is taken care of by Python scripts in
`src/evaluate`. The first step in evaluation is to amend each response
(each line in the response JSONL file) with its ground truth. Once
that is complete, frameworks are engaged that judge the response.

There are currently two frameworks used for judgement:

1. Custom OpenAI (`src/evaluate/openai_`): request an OpenAI model to
   assess similarity using a custom user prompt. By default, the
   OpenAI model that is used to judge is different from the model used
   to respond.

2. Deepeval (`src/evaluate/deepeval_`): Deepeval is an open source
   framework used for LLM response evaluation.

This process can be run from `bin/run-evals.sh` as follows:

```bash
./bin/run-evals.sh -u /data/prompts/user -g /data/ground-truth < responses.jsonl > evaluations.jsonl
```

This will produce `evaluations.jsonl`, a JSONL file that is a super set
of `responses.jsonl`: each line includes all information from the LLM
response, in addition to the output of the judgement. As such, the two
commands can be piped together:

```bash
./bin/run-prompts.sh ... | ./bin/run-evals.sh > evaluations.jsonl
```

without loss of information. See `./bin/run-evals.sh -h` for
documentation, other options, and insight into the Python scripts that
are doing the work.

## Analysis

Analysis can be conducted by parsing relevant information from the
final evaluation JSON. Some basic analysis is included in this
repository.

First convert the JSONL into CSV:

```bash
tmp=`mktemp`
python src/analysis/json-to-csv.py \
    --name-length 5 \
    --method gpt-4o-2024-08-06:custom \
    < $evaluations.jsonl \
    > $tmp
```

The options provided to `json-to-csv.py` shorten prompt names to five
characters, and focus JSON filtering to the OpenAI
judgements. Performance plots can be built using:

```bash
python src/analysis/plot-scores.py --output scores.png < $tmp
mkdir responses
python src/analysis/plot-responses.py --output responses < $tmp
rm $tmp
```

## Output format

The output from each step is a JSONL file. What each line represents
depends on which part of the pipeline produced the file; whether it
was the response or the evaluation phase. Irrespective, each phase
appends to a given line -- information is never overwritten.

```python
{
  # ADDED DURING EXPERIMENT SETUP PHASE
  "system": str,          # system prompt: basename /data/prompts/system/system-file-n
  "user": str,            # system prompt: basename /data/prompts/user/user-file-n
  "docs": str,            # document set: (/data/documents/)method_n/instance_n
  "sequence": int,        # response iteration

  # ADDED DURING LLM PROMPTING PHASE
  "response": [           # see mylib/_experiment.py::ExperimentResponse
    {
       "message": str,    # LLM response
       "model": str       # OpenAI model
       "latency": float   # request latency in seconds
       "response_id": str # Auto-generated unique ID
       "date": datetime   # Time when response was generated
    }
  ],

  # ADDED DURING JUDGEMENT PHASE
  "comparison": int,      # comparison iteration
  "reference": str,       # ground truth: basename /data/ground-truth/user-file-n/file-n
  "judgement": [
    {
       "method": str,     # Judgement platform
       "score": float,    # LLM score
       "support": Any     # Material supporting the judgement (platform dependent)
    }
  ]
}
```

The `responses.jsonl` file mentioned earlier will include material
from the "experiment setup phase" and "LLM prompting phase". The
`evaluations.jsonl` will include that, along with material from
"judgement phase".
