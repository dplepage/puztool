import re
from urllib.request import urlopen, quote
from pyquery import PyQuery as pq
import pandas as pd

qaturl = "http://www.quinapalus.com/cgi-bin/qat?pat={}&ent=Search&dict=0"

statre = re.compile('(?P<early>Search terminated early)? *Total solutions found: (?P<count>\d+) in (?P<time>.*?)s')

def extract_from_table(table):
    for row in table('tr').items():
        yield [col.text().strip() for col in row('td').items()]

class StructureChanged(Exception):
    '''If this is raised, it means qat's page structure changed.

    If that happens, this script probably stops working.
    '''
    pass

class Response(object):
    def __init__(self, early, count, time, l):
        super(Response, self).__init__()
        self.early = early
        self.count = count
        self.time = time
        self.l = l
        self.status = '{} items in {}s{}'.format(self.count, self.time, ' (e)' if self.early else '')

    def __repr__(self):
        return 'Response({!r}, {!r}, {!r})'.format(self.early, self.count, self.time)

    def __str__(self):
        return '<{}>'.format(self.status)


def _qat(pattern):
    x = pq(urlopen(qaturl.format(quote(pattern))).read())
    status = x(".in i").text()
    stats = statre.match(status)
    early = bool(stats.group('early'))
    count = int(stats.group('count'))
    time = float(stats.group('time'))
    table = x(".in form + table")
    if len(table) > 1:
        raise StructureChanged("Multiple matches for .in form + table")
    if len(table) == 1:
        entries = extract_from_table(table)
    else:
        lines = x(".in").clone().children().remove().end().text().splitlines()
        entries = [l.split() for l in lines if l.strip()]
        entries = sum(entries, [])
    return Response(early, count, time, entries)


def qat(pattern, verbose=True, df=True):
    result = _qat(pattern)
    if verbose:
        print(result.status)
    if df:
        return pd.DataFrame(result.l)
    return result.l


if __name__ == '__main__':
    import sys
    results = qat(sys.argv[1])
    for row in results:
        if isinstance(row, list):
            print(''.join('{:10}'.format(x) for x in row))
        else:
            print(row)
