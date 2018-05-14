from bs4 import BeautifulSoup

from .service import Service, QueryError


class NutrimaticService(Service):
    urlbase = "http://nutrimatic.org/?q={}"

    def parse_page(self, query, html):
        page = BeautifulSoup(html, 'lxml')
        if b'error' in html:
            raise QueryError(page.select_one("font").text)
        items = [s.text for s in page.select("span")]
        partial = b'No more results found.' not in html
        return items, partial, None

nutr = nutrimatic = NutrimaticService()


if __name__ == '__main__':
    import sys
    print(nutr(sys.argv[1]))
