# -*- coding: utf-8 -*-
'''A webbot for doing useful things.

This runs a flask app where posting a string to /puzz will run a command and
send the result to a target url. Commands include things like qat, nutrimatic,
braille, etc. This is particularly useful if you spin it up somewhere public and
make slack commands that point to it: from within your slack, you'll then be
able to do e.g. `/puzz qat fooA;barA` and it'll print the list of matching
results.
'''
import multiprocessing as mp

import requests
from flask import Flask, request, jsonify
from puztool.service import QueryError, StructureChanged
from puztool.service import qat, nutr, wordsmith, unphone, onelook, qatpat
from puztool import morse, nato
from puztool.phone import to_phone
import funcy as fn

application = app = Flask(__name__)


def run_service(service, query, limit=10):
    try:
        result = service(query, verbose=False, fmt='raw')
    except (QueryError, StructureChanged) as p:
        url = service.ext_url(query)
        return dict(text=f"<{url}|Query failed>:{query}")
    url = service.ext_url(query)
    results = result.l[:limit]
    resp = "\n".join(l if isinstance(l, str) else '\t'.join(l) for l in results)
    count = len(results)
    if count < limit:
        cstr = f'{count}'
    elif result.total is None:
        cstr = f'First {count}'
    else:
        cstr = f'First {count} of {result.total}'
    text = f"{cstr} {service.name} results for `{query}` <{url}|(go to site)>."
    blocks = [{
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": text
        },
        "block_id": "text1"
    }]
    if resp:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": resp,
            },
        })
    return dict(
        blocks = blocks,
        text = text,
        response_type= "in_channel",
    )

def run_iterable(iterable, name, query, limit=20):
    try:
        items = list(fn.take(limit, iterable))
    except Exception as e:
        return dict(text=f"Query failed:{e}")
    resp = "\n".join("".join(l.val) for l in items[:limit])
    count = len(items)
    if count < limit:
        cstr = f'{count}'
    else:
        cstr = f'First {count}'
    return {
        "text": f"{cstr} results for `{name}({query})`.",
        "response_type": "in_channel",
        "attachments": [
            {
                "text":resp
            }
        ]
    }


def defer(fn, target, *args):
    if target is None:
        f = fn(*args)
        print(f)
        return f
    def doit():
        try:
            response = fn(*args)
        except Exception as e:
            requests.post(target, json=dict(
                text = f"Query failed: {e}",
                response_type = "in_channel",
            ))
            return
        x = requests.post(target, json=response)
        if x.status_code != 200:
            requests.post(target, json=dict(
                text = f"Status post failed with status {x.status_code}",
                response_type = "in_channel",
            ))
    p = mp.Process(target=doit)
    p.start()
    return p

help_msg = dict(
    text = '''
Usage: `/puzz <cmd> <query>`
Search commands:
> *qat* - Get matches with <https://www.quinapalus.com/cgi-bin/qat|Qat>
> *nutrimatic* - Get matches with <https://nutrimatic.org/|Nutrimatic>
> *onelook* - Get matches with <https://onelook.com/|OneLook>
> *anagram* - Get anagrams from <https://wordsmith.org/anagram/|Wordsmith>
> *unphone* - Get words from a phone # from <http://www.dialabc.com/words/search/index.html|DialABC>

Conversion commands:
> *braille*/*unbraille* - Convert text to <https://en.wikipedia.org/wiki/Braille|braille>
> *phone* - Convert text to <https://en.wikipedia.org/wiki/Phoneword|a phone number>
> *morse*/*unmorse* - Convert text to or from <https://en.wikipedia.org/wiki/Morse_code|morse code>
> *nato*/*unnato* - Convert text to or from <https://en.wikipedia.org/wiki/NATO_phonetic_alphabet|nato phonetics>

Note that unmorse and unnato will simply ignore any word that isn't a recognized letter.
    '''.strip()
)


@app.route("/puzz", methods=["POST"])
def handle_cmd():
    query = request.form.get('text')
    if not query:
        return jsonify(help_msg)
    target = request.form['response_url']
    cmd, rest = query.split(maxsplit=1)
    if cmd not in fns:
        return jsonify({
            "text": f"No command matches: `{cmd}`...",
            "response_type": "ephemeral",
        })
    try:
        return fns[cmd](rest, target)
    except Exception as e:
        return jsonify({
            "text": f"Command `{query}` failed: {e}",
            "response_type": "ephemeral",
        })


fns = {}

def method(name):
    def wrapper(fn):
        @app.route(f"/{name}", methods=["POST"], endpoint=name)
        def endpoint():
            query = request.form['text']
            target = request.form['response_url']
            return fn(query, target)
        @app.route(f"/g/{name}/<query>", methods=["GET"], endpoint="g"+name)
        def g_endpoint(query):
            return fn(query, None)
        fns[name] = fn
        return fn
    return wrapper

def add_service(name, service, feedback):
    @method(name)
    def handle(query, target):
        defer(run_service, target, service, query)
        url = service.ext_url(query)
        return jsonify(dict(
            text=feedback.format(query=query, url=url),
            resposne_type='ephemeral'))

add_service('qat', qat, 'Asking <{url}|qat> to match `{query}`')
add_service('nutrimatic', nutr, 'Asking <{url}|Nutrimatic> to match `{query}`')
add_service('onelook', nutr, 'Asking <{url}|OneLook> to match `{query}`')
add_service('anagram', wordsmith, 'Finding <{url}|anagrams> for `{query}`')
add_service('wordsmith', wordsmith, 'Finding <{url}|anagrams> for `{query}`')
add_service('unphone', unphone, 'Finding <{url}|phone matches> for `{query}`')
add_service('isomorph', qatpat, 'Finding <{url}|isomorphisms> for `{query}`')

def add_basic(name, fn):
    @method(name)
    def handle_it(query, target):
        text = ''.join(str(x) for x in fn(query))
        return jsonify(dict(
            text=f"`{text}`" if text else "Nothing to do...",
            response_type = 'in_channel'))
    return handle_it

class Braille:
    lookup = " A1B'K2L@CIF/MSP\"E3H9O6R^DJG>NTQ,*5<-U8V.%[$+X!&;:4\\0Z7(_?W]#Y)="
    @staticmethod
    def encode(text):
        s = Braille.lookup
        return ''.join(
            chr(0x2800+s.index(t)) if t in s else '?' for t in text.upper())

    @staticmethod
    def decode(text):
        s = Braille.lookup
        return ''.join(s[ord(t)-0x2800] if 0x2800 <= ord(t) < 0x2840 else '?'
            for t in text)

add_basic("morse", morse.encode)
add_basic("unmorse", morse.decode)
add_basic("nato", nato.encode)
add_basic("unnato", nato.decode)
add_basic("phone", to_phone)
add_basic('braille', Braille.encode)
add_basic('unbraille', Braille.decode)

if __name__ == '__main__':
    app.run(debug=True)
