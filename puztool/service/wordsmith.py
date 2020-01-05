import re
from bs4 import BeautifulSoup

from .service import Service, StructureChanged


class WordsmithService(Service):
    urlbase = "https://new.wordsmith.org/anagram/anagram.cgi?anagram={{{}}}&t=20"
    statre = re.compile(r'(?P<total>\d+) found. Displaying')

    def ext_url(self, query):
        return self.mkurl(query)[:-2]+"500"

    def parse_page(self, query, page):
        page = BeautifulSoup(page, 'lxml')
        p = page.select_one(".p402_premium")
        if p is None:
            return [], False, 0
        status = page.select_one(".p402_premium > b").text
        stats = self.statre.match(status)
        if not stats:
            raise StructureChanged('No header block')
        total = int(stats.group('total'))
        entries = ''.join(p.findAll(text=True, recursive=False)).strip().splitlines()
        entries = [e.strip() for e in entries if e.strip() not in ['', 'YOUR PREMIUM CONTENT HERE']]
        return entries, len(entries) < total, total

wordsmith = WordsmithService()


if __name__ == '__main__':
    import sys
    print(wordsmith(sys.argv[1]))
