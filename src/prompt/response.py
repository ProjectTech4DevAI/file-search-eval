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

from mylib import Logger, ExperimentResponse, FileIterator

@dataclass(frozen=True)
class Resource:
    response: str
    vector_store: str

@dataclass(frozen=True)
class Job:
    resource: Resource
    model: str
    config: dict

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

class VectorStoreCleaner(ResourceCleaner):
    def clean(self, client):
        for i in vs_ls(self.resource, client):
            client.files.delete(i.id)
        client.vector_stores.delete(self.resource)

class ResponseCleaner(ResourceCleaner):
    def clean(self, client):
        client.responses.delete(self.resource)

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
    def __init__(self, client, args):
        super().__init__(client, args)
        self.ls = FileIterator(self.args.upload_batch_size)

    def create(self, config, **kwargs):
        documents = self.args.document_root.joinpath(config['docs'])
        vector_store = self.client.vector_stores.create()

        for paths in self.ls(documents):
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

class ResponseCreator(ResourceCreator):
    _kwargs = (
        'model',
        'vector_store',
        'question',
    )

    def create(self, config, **kwargs):
        model, vector_store_id, question = map(kwargs.get, self._kwargs)
        instructions = scanp(config, self.args.prompt_root, 'system')

        response = self.client.responses.create(
            model=model,
            instructions=instructions,
            tools=[
                {
                    "type": "file_search",
                    "vector_store_ids": [vector_store_id],
                    "max_num_results": 20,
                }
            ],
            temperature=0.1,
            input=[{"role": "user", "content": question}],
            include=["file_search_call.results"],
        )

        return response

@dataclass(frozen=True)
class ResourceKey:
    docs: str
    model: str

class OpenAIResources:
    _resources = (
        (ResponseCreator, ResponseCleaner),
        (VectorStoreCreator, VectorStoreCleaner),
    )

    def __init__(self, args):
        self.args = args

        self.client = OpenAI()
        self.resources = {}
        (self.r_creator, self.v_creator) = (
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
            question = scanp(config, self.args.prompt_root, 'user')
            for model in self.args.model:
                key = ResourceKey(docs, model)
                resource = self.resources.get(key)
                if resource is None:
                    vector_store = self.v_creator(config)
                    response = self.r_creator(
                        config,
                        model=model,
                        vector_store=vector_store,
                        question=question,
                    )
                    resource = Resource(response, vector_store)
                    self.resources[key] = resource

                yield Job(resource, model, config)

def func(incoming, outgoing, session_id, args):
    import datetime
    client = OpenAI()
    creator = ResponseCreator(client, args)

    while True:
        job = incoming.get()
        Logger.info(job)

        question = scanp(job.config, args.prompt_root, 'user')
        start = time.time()

        response = creator.create(
            job.config,
            model=job.model,
            vector_store=job.resource.vector_store,
            question=question,
        )

        latency = time.time() - start

        outgoing.put({
            "system": job.config["system"],
            "user": job.config["user"],
            "docs": job.config["docs"],
            "sequence": job.config.get("sequence", 0),
            "response": [
                {
                    "message": response.output_text,
                    "model": job.model,
                    "latency": latency,
                    "response_id": response.id,
                    "date": datetime.datetime.now().ctime()
                }
            ]
        })

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
        incoming,
        outgoing,
        str(uuid4()),
        args,
    )

    with Pool(args.workers, func, initargs):
        with OpenAIResources(args) as resources:
            jobs = 0
            for i in resources(sys.stdin):
                incoming.put(i)
                jobs += 1

            for _ in range(jobs):
                result = outgoing.get()
                print(json.dumps(result))
