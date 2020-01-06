import time
from urllib.request import urlopen, quote
import pandas as pd

class StructureChanged(Exception):
    '''Exception for "we parsed a page and it wasn't what we expected".

    Usually this means the service has changed their website and so this
    integration will no longer work.
    '''
    pass

class QueryError(ValueError):
    '''Raised when a service reports a bad input.'''
    pass


class Result(object):
    def __init__(self, query, url, total, time, partial, items):
        super(Result, self).__init__()
        self.query = query
        self.url = url
        self.total = total
        self.partial = partial
        self.time = time
        self.l = items
        pstr = ' (partial)' if partial else ''
        self.status = f'{len(self.l)} items in {self.time}s{pstr}'

    def __repr__(self):
        return 'Result({!r}, {!r}, {!r})'.format(self.early, self.count, self.time)

    def __str__(self):
        return '<{}>'.format(self.status)

class Service:
    def ext_url(self, query):
        raise NotImplementedError()

    def get_results(self, query):
        raise NotImplementedError()

    def search(self, query, verbose=True, fmt='df'):
        start = time.perf_counter()
        items, partial, total = self.get_results(query)
        end = time.perf_counter()
        url = self.ext_url(query)
        result = Result(query, url, total, end-start, partial, items)
        if verbose:
            print(result.status)
        if fmt == 'l':
            return list(result.l)
        if fmt == 'df':
            return pd.DataFrame(result.l)
        return result

    def __call__(self, query, verbose=True, fmt='df'):
        return self.search(query, verbose, fmt)



class ScraperService(Service):
    @property
    def urlbase(self):
        raise NotImplementedError()

    def mkurl(self, query):
        return self.urlbase.format(quote(query))

    def ext_url(self, query):
        return self.mkurl(query)

    def get_results(self, query):
        url = self.mkurl(query)
        page = urlopen(url).read()
        return self.parse_page(query, page)

    def parse_page(self, query, page):
        raise NotImplementedError()
