import re
from string import ascii_uppercase as uppers
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

class PatMatch(QatService):
    '''Simple pattern-matching via qat.

    This behaves just like QatService, except it adds constraints that every
    variable in the expression must have length 1 and be distinct. Thus,
    a query for ABACA will be expanded to the query
    ACABC;|A|=1;|B|=1;|C|=1;!=ABC

    This is particularly useful when solving substitution ciphers - given a
    string like QGQDLATAHL, for example, it will tell you that the only match
    know to qat is SUSTENANCE.
    '''
    def expand_query(self, query):
        chars = set(query) & set(uppers)
        for c in chars:
            query+=f';|{c}|=1'
        query+=f';!={"".join(chars)}'
        return query

    def mkurl(self, query):
        return super()(self.expand_query(query))

qat = QatService()


if __name__ == '__main__':
    import sys
    print(qat(sys.argv[1]))
