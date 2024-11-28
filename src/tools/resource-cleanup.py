import time
import json
import logging
import operator as op
from pathlib import Path
from argparse import ArgumentParser

from openai import OpenAI, NotFoundError

class ResourceManager:
    def __init__(self, client):
        self.client = client

    def __iter__(self):
        kwargs = {}

        while True:
            page = self.view(**kwargs)
            yield from page
            if not page.has_more:
                break
            kwargs['after'] = page.last_id

class VectorStoreManager(ResourceManager):
    def __init__(self, client, vector_store_id):
        super().__init__(client)
        self.vector_store_id = vector_store_id

    def view(self, **kwargs):
        return self.client.beta.vector_stores.files.list(
            vector_store_id=self.vector_store_id,
            **kwargs,
        )

class AssistantsManager(ResourceManager):
    def view(self, **kwargs):
        return self.client.beta.assistants.list(**kwargs)

#
#
#
def stores(assistant_id):
    if assistant_id.tool_resources.file_search is not None:
        yield from assistant_id.tool_resources.file_search.vector_store_ids


if __name__ == '__main__':
    client = OpenAI()
    assistants = AssistantsManager(client)

    remove = []
    for a in assistants:
        logging.critical(a.id)
        for s in stores(a):
            vectors = VectorStoreManager(client, s)
            resources = [ x.id for x in vectors ]
            for r in resources:
                client.files.delete(r)
            client.beta.vector_stores.delete(s)
        remove.append(a.id)

    for a in remove:
        try:
            client.beta.assistants.delete(a)
        except NotFoundError:
            logging.error(a)
