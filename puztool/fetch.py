'''Tools for parsing data out of websites.

These are mediocre, because websites are terrible, but it's frequently good
enough.

The two main fns are fetch_list and fetch_table; see docstrings for more info.

'''

import re
import requests
from bs4 import BeautifulSoup
import pandas as pd

def filterer(filter):
    def newfn(s):
        m = re.match(filter, s)
        if m: return m.groupdict()
    return newfn

def parse_list(elements, filter=re.compile('(?P<value>.*)'), cols=None, html=False):
    '''Extract text from a list of bs4 elements to a pandas dataframe.

    `filter` should be a function that takes a string and returns a dictionary
    of values. It can also be a regex with named subgroups, in which case it
    treated as lambda s:re.match(filter, s).groupdict().

    If the filter returns None (i.e., doesn't match) for an element, that
    element will be skipped.

    `cols` provides an ordered list of columns for the data frame; if none is
    provided it will be inferred from the values, but in this case the column
    order may not be deterministic.
    '''
    if isinstance(filter, str):
        filter = re.compile(filter)
    if isinstance(filter, re._pattern_type):
        if cols is None:
            cols = list(filter.groupindex)
        filter = filterer(filter)
    data = []
    for elt in elements:
        if html:
            text = str(elt)
        else:
            text = elt.text
        match = filter(text)
        if match is None:
            continue
        data.append(match)
    return pd.DataFrame(data, columns=cols)

def select(url, selector):
    '''Download a url and select elements from it.'''
    resp = requests.get(url)
    soup = BeautifulSoup(resp.content, 'lxml')
    return soup.select(selector)

def fetch_list(url, selector, filter=re.compile('(?P<value>.*)'), cols=None, html=False):
    '''
    Attempt to download a list of data from a website.

    url is the url of the page to scrape; selector should be a css selector. If
    regex is not specified, this will find all elements in the page matching the
    given selector and return a dataframe with a single column, 'value',
    containing the text part of each such element.

    If regex IS provided, the return value will have one column for each named
    subgroup of the regex. Each selected element's text will be parsed according
    to the regex, and the named subgroup values will be used to populate the
    dataframe; elements that don't match will be ignored.

    '''
    return parse_list(select(url, selector), filter, cols, html)


def fetch_table(url, wiki=True, **kw):
    '''Just a thin wrapper around pd.read_html.'''
    text = requests.get(url).content
    if wiki: # wikipedia mode - remove footnotes and other details
        bs = BeautifulSoup(text, 'lxml')
        [x.decompose() for x in bs.findAll("small")]
        [x.decompose() for x in bs.select(".reference")]
        text = str(bs)
    return pd.read_html(text, **kw)
