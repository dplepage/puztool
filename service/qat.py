import re

from .service import Service, QueryError, StructureChanged


class QatService(Service):
    urlbase = "http://www.quinapalus.com/cgi-bin/qat?pat={}&ent=Search&dict=0"
    statre = re.compile('(?P<early>Search terminated early)? *Total solutions found: (?P<count>\d+) in (?P<time>.*?)s')

    def parse_page(self, query, page):
        status = page(".in i").text()
        stats = self.statre.match(status)
        if not stats:
            raise QueryError(query)
        partial = bool(stats.group('early'))
        table = page(".in form + table")
        if len(table) > 1:
            raise StructureChanged("Multiple matches for .in form + table")
        if len(table) == 1:
            entries = self.extract_from_table(table)
        else:
            lines = page(".in").clone().children().remove().end().text().splitlines()
            entries = [l.split() for l in lines if l.strip()]
            entries = sum(entries, [])
        return entries, partial

    def extract_from_table(self, table):
        for row in table('tr').items():
            yield [col.text().strip() for col in row('td').items()]

qat = QatService()


if __name__ == '__main__':
    print(qat("potat*"))
