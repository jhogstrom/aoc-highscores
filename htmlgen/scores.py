import pathlib
import json
import logging
import requests

class DataRepresentation():
    def __str__(self):
        return self.Filename()

    def __eq__(self, other):
        return isinstance(other, type(self)) \
            and self.url == other.url \
            and self.filename == other.filename

    def __hash__(self):
        return hash(f"{self.filename()}*{self.url()}")

    def filename(self):
        raise NotImplementedError

    def url(self):
        raise NotImplementedError


class Downloader():
    def __init__(self, sessionid: str = None):
        self.jar = requests.cookies.RequestsCookieJar()
        if sessionid:
            self.jar.set("session", sessionid, domain=".adventofcode.com", path='/')
        else:
            logging.warning("NOT setting sessionid")

    def get_data(self, representation: DataRepresentation):
        url = representation.url()
        logging.debug(f"Downloading from {url}")
        headers = {'user-agent': 'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.0; .NET CLR 1.0.3705)'}
        r = requests.get(url, cookies=self.jar, headers=headers)
        logging.debug(f"Downloading done... [{r.content.decode()[:20]}]")
        return r.content.decode()

class Cache():
    def has_data(self, representation: DataRepresentation) -> bool:
        raise NotImplementedError

    def add_data(self, representation: DataRepresentation, data) -> None:
        raise NotImplementedError

    def get_raw(self, representation) -> str:
        raise NotImplementedError

class FileCache(Cache):
    def __init__(self, rootdir: pathlib.Path):
        self.rootdir = rootdir
        if not rootdir.exists():
            logging.debug(f"Creating {rootdir}")
            rootdir.mkdir()

    def has_data(self, representation: DataRepresentation) -> bool:
        filename = self.rootdir / representation.filename()
        exists = filename.exists()
        logging.debug(f"Checking if {filename} exists... {exists}")
        return exists

    def add_data(self, representation: DataRepresentation, data) -> None:
        logging.debug(f"Adding cache for {representation}")
        filename = self.rootdir / representation.filename()
        with codecs.open(filename, 'w', "utf-8") as f:
            f.write(data)

    def get_raw(self, representation) -> str:
        logging.debug(f"Retrieving cached {representation}")
        filename = self.rootdir / representation.filename()
        with open(filename, encoding='utf-8') as f:
            return f.read()


class DataRetriever():
    def __init__(self, downloader: Downloader, cache: Cache):
        self.downloader = downloader
        self.cache = cache

    def ensure_cached(self, representation: DataRepresentation):
        if not self.cache.has_data(representation):
            data = self.downloader.get_data(representation)
            self.cache.add_data(representation, data)

    def get_data(self, representation: DataRepresentation):
        self.ensure_cached(representation)
        s = self.cache.get_raw(representation)
        return json.loads(s)

    def get_raw(self, representation: DataRepresentation):
        self.ensure_cached(representation)
        return self.cache.get_raw(representation)

if __name__ == "__main__":
    import aocgen
    raise Exception("This is just a module!")