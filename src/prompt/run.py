import sys
import json
import time
import logging
import collections as cl
from pathlib import Path
from argparse import ArgumentParser

from openai import OpenAI, NotFoundError

#
#
#
class PromptReader:
    def __init__(self, config, root):
        self.config = config
        self.root = root

    def __call__(self, ptype):
        return (self
                .root
                .joinpath(ptype, self.config[ptype])
                .read_text())

#
#
#
class ResourceCleaner:
    def __init__(self, resource):
        self.resource = resource

    def __call__(self, client, retries=1):
        for _ in range(retries):
            try:
                self.clean(client)
                break
            except NotFoundError:
                pass
        else:
            logging.error('Cannot clean %s', type(self).__name__)

    def clean(self, client):
        raise NotImplementedError()

class MessageCleaner(ResourceCleaner):
    def __init__(self, resource, thread):
        super().__init__(resource)
        self.thread = thread

    def clean(self, client):
        client.beta.threads.messages.delete(
            message_id=self.resource,
            thread_id=self.thread,
        )

class ThreadCleaner(ResourceCleaner):
    def	clean(self, client):
        client.beta.threads.delete(self.resource)

class AssistantCleaner(ResourceCleaner):
    def clean(self, client):
        client.beta.assistants.delete(self.resource)

class VectorStoreCleaner(ResourceCleaner):
    def clean(self, client):
        kwargs = {}
        while True:
            page = client.beta.vector_stores.files.list(
                vector_store_id=self.resource,
                **kwargs,
            )
            for file_ in page:
                client.files.delete(file_.id)
            if not page.has_more:
                break
            kwargs['after'] = page.last_id
        client.beta.vector_stores.delete(self.resource)

#
#
#
def ls(root, limit):
    batch = []

    for i in root.rglob('*.md'):
        batch.append(i)
        if len(batch) >= limit:
            yield batch
            batch = []

    if batch:
        yield batch

#
#
#
if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--prompt-root', type=Path)
    arguments.add_argument('--document-root', type=Path)
    arguments.add_argument('--cleanup-attempts', type=int, default=3)
    arguments.add_argument('--upload-batch-size', type=int, default=20)
    args = arguments.parse_args()

    #
    # Setup
    #

    config = json.load(sys.stdin)
    logging.critical(
        ' '.join(str(config.get(x)) for x in ('system', 'user', 'sequence'))
    )
    reader = PromptReader(config, args.prompt_root)
    client = OpenAI()

    #
    # Create the vector store
    #

    vector_store = client.beta.vector_stores.create()
    vector_store_cleaner = VectorStoreCleaner(vector_store.id)

    documents = args.document_root.joinpath(config['docs'])
    for paths in ls(documents, args.upload_batch_size):
        nfiles = len(paths)
        logging.warning('Uploading %d', nfiles)

        files = [ x.open('rb') for x in paths ]
        file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vector_store.id,
            files=files,
        )
        for i in files:
            i.close()

        if file_batch.file_counts.completed != nfiles:
            vector_store_cleaner(client, args.cleanup_attempts)
            raise IndexError(
                'Failure "upload_and_poll": uploaded %d of %d',
                file_batch.file_counts,
                nfiles,
            )

    #
    # Create the assistant
    #

    assistant = client.beta.assistants.create(
        model=config['model'],
        instructions=reader('system'),
        temperature=1e-4,
        tools=[{
            'type': 'file_search',
        }],
        tool_resources={
            'file_search': {
                'vector_store_ids': [
                    vector_store.id,
                ],
            },
        },
    )

    #
    # Send the prompt
    #

    thread = client.beta.threads.create()
    message = client.beta.threads.messages.create(
        thread.id,
        role='user',
        content=reader('user'),
    )
    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread.id,
        assistant_id=assistant.id,
    )

    if run.status == 'completed':
        response = client.beta.threads.messages.list(
            thread_id=thread.id,
            run_id=run.id,
        )
        result = response.data[0].content[0].text.value
    else:
        logging.error('%s %s', config, run)
        result = None

    #
    # Clean up
    #

    cleaners = (
        MessageCleaner(message.id, thread.id),
        ThreadCleaner(thread.id),
        AssistantCleaner(assistant.id),
        vector_store_cleaner,
    )
    for c in cleaners:
        c(client, args.cleanup_attempts)

    #
    # Print the result
    #

    kwargs = cl.defaultdict(dict)
    kwargs['response'] = {
        'date': time.strftime('%c'),
        'message': result,
    }
    assert not any(x in config for x in kwargs)
    config.update(kwargs)

    print(json.dumps(config, indent=3))
