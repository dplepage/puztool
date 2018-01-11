from bs4 import BeautifulSoup

from .service import Service


class UnphoneService(Service):
    urlbase = "http://www.dialabc.com/words/search/index.html?pnum={}&dict=american&pad=ext&filter=normal"

    def parse_page(self, query, page):
        page = BeautifulSoup(page, 'lxml')
        entries = [b.text for b in page.select("td b") if len(b.text) == len(query)]
        return entries, False, len(entries)

unphone = UnphoneService()


if __name__ == '__main__':
    import sys
    print(unphone(sys.argv[1]))
