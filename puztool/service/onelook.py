import re
import json
from bs4 import BeautifulSoup
from urllib.request import quote
import datamuse

from .service import Service, StructureChanged


class OnelookService(Service):
    def ext_url(self, query):
        query = quote(query)
        return f"https://onelook.com/?w={query}&scwo=1"

    def get_results(self, query, max_results=20):
        api = datamuse.Datamuse(max_results=max_results)
        if ':' in query:
            sp, meaning = query.split(":", 1)
        else:
            sp, meaning = query, None
        words = api.words(sp=sp, ml=meaning)
        if len(words) < max_results:
            return [x['word'] for x in words], False, len(words)
        return [x['word'] for x in words], True, None

onelook = OnelookService()


if __name__ == '__main__':
    import sys
    print(onelook(sys.argv[1]))
