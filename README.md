# Veddis Evaluation

This repository automates OpenAI File Search testing

## Run

### Get responses to queries

For each combination of

* system prompt (`prompts/system`)
* user prompt (`prompts/user`)
* markdown files (`docs`)

generate completions from OpenAI File Search that are supported by the
markdown files. By default, each user prompt is sent multiple times to
test consistency.

Response generation happens in two phases. In the first "experiments"
are created specifying which system prompt, user prompt, markdown
files, and user prompt iteration is being tested. In the second phase
each experiment file is used to setup a File Search interaction,
including a vector store, assistant, thread, and message. The resouces
are deleted once the query has completed.

The entire process can be run from `bin/run-prompts.sh` as follows:

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

3. Create a directory to store the output

   ```bash
   $> mkdir var
   ```

4. Generate the experiments and begin prompting

   ```bash
   $> ./bin/run-prompts.sh -o var
   ```

Experiment configurations and LLM responses will be stored in `var`
(`/experiments` and `/results`, respectively) as JSON files.
