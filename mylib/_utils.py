def walk(path):
    for i in path.iterdir():
        if not i.is_dir():
            yield i
        else:
            yield from walk(i)

class FileIterator:
    def __init__(self, batch_size):
        self.batch_size = batch_size

    def __call__(self, root):
        batch = []
        for p in walk(root):
            batch.append(p)
            if len(batch) >= self.batch_size:
                yield batch
                batch = []

        if batch:
            yield batch
