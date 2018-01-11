import re
from bs4 import BeautifulSoup

from .service import Service, StructureChanged


class WordsmithService(Service):
    urlbase = "https://new.wordsmith.org/anagram/anagram.cgi?anagram={{{}}}&t=20"
    statre = re.compile('(?P<total>\d+) found. Displaying')

    def ext_url(self, query):
        return self.mkurl(query)[:-2]+"500"

    def parse_page(self, query, page):
        page = BeautifulSoup(page, 'lxml')
        p = page.select_one(".p402_premium > p")
        if p is None:
            return [], False, 0
        status = p.select_one("b").text
        stats = self.statre.match(status)
        if not stats:
            raise StructureChanged('No header block')
        total = int(stats.group('total'))
        entries = ''.join(p.findAll(text=True, recursive=False)).strip().splitlines()
        return entries, len(entries) < total, total

    def extract_from_table(self, table):
        for row in table.select('tr'):
            yield [col.text.strip() for col in row.select('td')]

wordsmith = WordsmithService()


if __name__ == '__main__':
    import sys
    print(wordsmith(sys.argv[1]))
