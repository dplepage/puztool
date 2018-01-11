import re
from bs4 import BeautifulSoup

from .service import Service, QueryError, StructureChanged


class NutrimaticService(Service):
    urlbase = "http://nutrimatic.org/?q={}"

    def parse_page(self, query, html):
        if 'error' in html:
            raise PatternError(x("font").text())
        page = BeautifulSoup(html, 'lxml')
        items = [s.text for s in page.select("span")]
        partial = 'No more results found.' not in html
        return items, partial, None

nutr = nutrimatic = NutrimaticService()


if __name__ == '__main__':
    import sys
    print(nutr(sys.argv[0]))
