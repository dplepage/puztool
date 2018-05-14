import re
from bs4 import BeautifulSoup

from .service import Service, QueryError, StructureChanged


class QatService(Service):
    urlbase = "http://www.quinapalus.com/cgi-bin/qat?pat={}&ent=Search&dict=0"
    statre = re.compile('(?P<early>Search terminated early)? *Total solutions found: (?P<count>\d+) in (?P<time>.*?)s')

    def parse_page(self, query, page):
        page = BeautifulSoup(page, 'lxml')
        status = page.select(".in i")[0].text
        stats = self.statre.match(status)
        if not stats:
            raise QueryError(query)
        partial = bool(stats.group('early'))
        tables = page.select(".in form + table")
        if len(tables) > 1:
            raise StructureChanged("Multiple matches for .in form + table")
        if len(tables) == 1:
            entries = self.extract_from_table(tables[0])
        else:
            texts = page.select(".in")[0].findAll(text=True, recursive=False)
            entries = ''.join(texts).split()
        return entries, partial, None

    def extract_from_table(self, table):
        for row in table.select('tr'):
            yield [col.text.strip() for col in row.select('td')]

qat = QatService()


if __name__ == '__main__':
    import sys
    print(qat(sys.argv[1]))
