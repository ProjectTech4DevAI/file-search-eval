import sys
import json
import math
import time
import operator as op
import itertools as it
from uuid import uuid4
from pathlib import Path
from argparse import ArgumentParser
from dataclasses import dataclass, astuple, asdict
from multiprocessing import Pool, Queue

import pandas as pd
from openai import OpenAI, OpenAIError, NotFoundError

from mylib import Logger, ExperimentResponse

#
#
#
@dataclass(frozen=True)
class Resource:
    assistant: str
    vector_store: str

@dataclass(frozen=True)
class Job:
    resource: Resource
    model: str
    config: dict

#
#
#
def vs_ls(vector_store_id, client):
    kwargs = {}
    while True:
        page = client.vector_stores.files.list(
            vector_store_id=vector_store_id,
            **kwargs,
        )
        yield from page
        if not page.has_more:
            break
        kwargs['after'] = page.last_id

def scanp(config, root, ptype):
    return (root
            .joinpath(ptype, config[ptype])
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
            Logger.error('Cannot clean %s', type(self).__name__)

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
    def clean(self, client):
        client.beta.threads.delete(self.resource)

class AssistantCleaner(ResourceCleaner):
    def clean(self, client):
        client.beta.assistants.delete(self.resource)

class VectorStoreCleaner(ResourceCleaner):
    def clean(self, client):
        for i in vs_ls(self.resource, client):
            client.files.delete(i.id)
        client.vector_stores.delete(self.resource)

#
#
#
class ResourceCreator:
    def __init__(self, client, args):
        self.client = client
        self.args = args

    def __call__(self, config, **kwargs):
        handle = self.create(config, **kwargs)
        return handle.id

    def create(self, config, **kwargs):
        raise NotImplementedError()

class VectorStoreCreator(ResourceCreator):
    @staticmethod
    def ls(root, limit):
        batch = []

        for i in root.rglob('*.md'):
            batch.append(i)
            if len(batch) >= limit:
                yield batch
                batch = []

        if batch:
            yield batch

    def create(self, config, **kwargs):
        documents = self.args.document_root.joinpath(config['docs'])
        vector_store = self.client.vector_stores.create()

        for paths in self.ls(documents, self.args.upload_batch_size):
            Logger.info('Uploading %d', len(paths))

            files = [ x.open('rb') for x in paths ]
            file_batch = (self
                          .client
                          .vector_stores
                          .file_batches.upload_and_poll(
                              vector_store_id=vector_store.id,
                              files=files,
                          ))
            for i in files:
                i.close()
            self.raise_for_status(file_batch, vector_store, paths)

        return vector_store

    def raise_for_status(self, response, vector_store, paths):
        assert response.file_counts.total == len(paths)

        if response.file_counts.completed != response.file_counts.total:
            paths = { str(x.name): x for x in paths }

            for i in vs_ls(vector_store.id, self.client):
                if i.last_error is None:
                    document = self.client.files.retrieve(i.id)
                    paths.pop(document.filename)
            for i in paths.values():
                Logger.error('Upload error: %s', i)

            vector_store_cleaner = VectorStoreCleaner(vector_store.id)
            vector_store_cleaner(self.client, self.args.cleanup_attempts)

            raise IndexError('Upload failure ({} of {}): {}'.format(
                response.file_counts.failed,
                response.file_counts.total,
                ', '.join(map(str, paths.values())),
            ))

class AssistantCreator(ResourceCreator):
    _kwargs = (
        'model',
        'vector_store',
    )

    def create(self, config, **kwargs):
        (model, vector_store_id) = map(kwargs.get, self._kwargs)
        instructions = scanp(config, self.args.prompt_root, 'system')

        assistant = self.client.beta.assistants.create(
            model=model,
            instructions=instructions,
            temperature=1e-4,
            tools=[{
                'type': 'file_search',
            }],
            tool_resources={
                'file_search': {
                    'vector_store_ids': [
                        vector_store_id,
                    ],
                },
            },
        )

        return assistant

#
#
#
@dataclass(frozen=True)
class ResourceKey:
    docs: str
    model: str

class OpenAIResources:
    _resources = (
        (AssistantCreator, AssistantCleaner),
        (VectorStoreCreator, VectorStoreCleaner),
    )

    def __init__(self, args):
        self.args = args

        self.client = OpenAI()
        self.resources = {}
        (self.a_creator, self.v_creator) = (
            x(self.client, self.args) for (x, _) in self._resources
        )

    def __enter__(self):
        self.resources.clear()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        cleaners = list(map(op.itemgetter(1), self._resources))
        for resource in self.resources.values():
            for (MyCleaner, r) in zip(cleaners, astuple(resource)):
                cleaner = MyCleaner(r)
                cleaner(self.client, self.args.cleanup_attempts)

    def __call__(self, fp):
        for line in fp:
            config = json.loads(line)
            docs = config['docs']
            for model in self.args.model:
                key = ResourceKey(docs, model)
                resource = self.resources.get(key)
                if resource is None:
                    vector_store = self.v_creator(config)
                    assistant = self.a_creator(
                        config,
                        model=model,
                        vector_store=vector_store,
                    )
                    resource = Resource(assistant, vector_store)
                    self.resources[key] = resource

                yield Job(resource, model, config)

#
#
#
class ThreadRunner:
    @staticmethod
    def parse_wait_time(err):
        if err.code == 'rate_limit_exceeded':
            for i in err.message.split('. '):
                if i.startswith('Please try again in'):
                    (*_, wait) = i.split()
                    return (pd
                            .to_timedelta(wait)
                            .total_seconds())

        raise TypeError(err.code)

    def __init__(self, client, response_id):
        self.client = client
        self.response_id = response_id

    def __call__(self, job, thread):
        for i in it.count():
            try:
                t_start = time.perf_counter()
                run = self.client.beta.threads.runs.create_and_poll(
                    thread_id=thread.id,
                    assistant_id=job.resource.assistant,
                )
                t_end = time.perf_counter()
            except OpenAIError as err:
                Logger.critical(err)
                continue

            if run.status == 'completed':
                break
            if run.status == 'is_expired':
                self.client.beta.threads.runs.cancel(
                    thread_id=thread.id,
                    run_id=run.id,
                )

            try:
                rest = self.parse_wait_time(run.last_error)
            except TypeError:
                rest = None
            if rest is not None:
                rest = math.ceil(rest)
                Logger.warning('Sleeping %ds', rest)
                time.sleep(rest)

            Logger.error('%d / %s / %s', i, job.config, run)

        latency = t_end - t_start
        response = self.client.beta.threads.messages.list(
            thread_id=thread.id,
            run_id=run.id,
        )
        message = response.data[0].content[0].text.value

        return ExperimentResponse(
            message=message,
            model=job.model,
            latency=latency,
            response_id=self.response_id,
        )

#
#
#
def func(incoming, outgoing, response_id, args):
    user = 'user'
    client = OpenAI()
    runner = ThreadRunner(client, response_id)

    while True:
        job = incoming.get()
        Logger.info(job)

        #
        # Send the prompt
        #

        thread = client.beta.threads.create()
        content = scanp(job.config, args.prompt_root, user)
        message = client.beta.threads.messages.create(
            thread.id,
            role=user,
            content=content,
        )
        result = runner(job, thread)

        #
        # Clean up
        #

        cleaners = (
            MessageCleaner(message.id, thread.id),
            ThreadCleaner(thread.id),
        )
        for c in cleaners:
            c(client, args.cleanup_attempts)

        #
        # Report the result
        #

        record = job.config.setdefault('response', [])
        record.append(asdict(result))

        outgoing.put(job.config)

if __name__ == '__main__':
    arguments = ArgumentParser()
    arguments.add_argument('--prompt-root', type=Path)
    arguments.add_argument('--document-root', type=Path)
    arguments.add_argument('--model', action='append')
    arguments.add_argument('--cleanup-attempts', type=int, default=3)
    arguments.add_argument('--upload-batch-size', type=int, default=20)
    arguments.add_argument('--workers', type=int)
    args = arguments.parse_args()

    incoming = Queue()
    outgoing = Queue()
    initargs = (
        outgoing,
        incoming,
        str(uuid4()),
        args,
    )

    with Pool(args.workers, func, initargs):
        with OpenAIResources(args) as resources:
            jobs = 0
            for i in resources(sys.stdin):
                outgoing.put(i)
                jobs += 1

            for _ in range(jobs):
                result = incoming.get()
                print(json.dumps(result))
