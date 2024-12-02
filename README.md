# Document Supported LLM Evaluation

This repository automates OpenAI File Search testing.

## Setup

### Environment

1. Ensure your OpenAI key is in the environment

   ```bash
   $> export OPENAI_API_KEY=...
   ```

2. Ensure you have a proper Python environment. If you do not have the
   packages required in your default environment, consider creating a
   virtual one:

   ```bash
   $> python -m venv venv
   $> source venv/bin/activate
   $> pip install -r requirements.txt
   ```

3. (Optional) Set the Python log level:

   ```bash
   $> export PYTHONLOGLEVEL=info
   ```

   The default level is "warning", however most of the scripts produce
   useful information at "info". Valid values come from the [Python
   logging
   module](https://docs.python.org/3/library/logging.html#logging-levels).

### Prompts and documents

Gather the prompts and documents that will supply the tests. User and
system prompts are expected to live under a common directory:

```
/data/prompts/
├── system
│   ├── file-1
│   ├── file-2
│   ├── ...
│   └── file-n
└── user
    ├── file-1
    ├── file-2
    ├── ...
    └── file-n
```

## Run

There are two components to this repository: getting responses to
queries, and evaluating those responses. In this section, we will
assume you are using
[veddis-eval-data](https://github.com/ProjectTech4DevAI/veddis-eval-data). From
the root of this repository:

```bash
$> git clone https://github.com/ProjectTech4DevAI/veddis-eval-data.git
```

### Get responses to queries

For each combination of

* system prompt (`veddis-eval-data/prompts/system`)
* user prompt (`veddis-eval-data/prompts/user`)
* markdown files (`veddis-eval-data/docs`)

generate completions from OpenAI File Search that are supported by the
markdown files. By default, each user prompt is sent multiple times to
test consistency.

Response generation happens in two phases. In the first "experiments"
are created specifying the system prompt, user prompt, markdown files,
and user prompt iteration being tested. In the second phase each
experiment file is used to setup a File Search interaction, including
a vector store, assistant, thread, and message. The OpenAI resouces
are deleted once the query has completed.

The entire process can be run from `bin/run-prompts.sh` as
follows. Assuming your environment is setup:

```bash
$> ./bin/run-prompts.sh \
	-p veddis-eval-data/prompts \
	-d veddis-eval-data/docs \
	-g veddis-eval-data/responses > responses.jsonl
```

This will produce `responses.jsonl`, a JSONL file detailing each
prompt and the LLM's response. See `./bin/run-prompts.sh -h` for
documentation and other options.

### Obtain LLM judgements to responses

Once responses have been generated, they can be judged using an
LLM. See `docs/prompts/evaluate` for the prompts used to do this. As
with response generation, the process is done in two phases: generated
judgement experiments, then interact with the LLM based on those
experiment configurations.

This process can be run from `bin/run-evals.sh` as
follows. Environment and Veddis data from previous steps are still
assumed to hold:

```bash
$> ./bin/run-evals.sh \
	-g veddis-eval-data/responses \
	< responses.jsonl \
	> evaluations.jsonl
```

This will produce `evaluations.jsonl`, a JSONL file that is a superset
of `responses.jsonl`: each line includes all information from the LLM
response, in addition to the output of the judgement. As such, the two
commands can be piped together:

```bash
$> ./bin/run-prompts.sh ... | ./bin/run-evals.sh > evaluations.jsonl
```

without loss of information. See `./bin/run-evals.sh -h` for
documentation and other options.
