# -*- coding: utf-8 -*-
import multiprocessing as mp

from flask import Flask, request, jsonify
import requests
from puztool.service import QueryError, StructureChanged
from puztool.service import qat, nutr, wordsmith, unphone
from puztool import morse, nato
from puztool.phone import to_phone
import funcy as fn

application = app = Flask(__name__)


def run_service(service, query):
    try:
        result = service(query, verbose=False, fmt='raw')
    except (QueryError, StructureChanged) as p:
        url = service.mkurl(query)
        return dict(text=f"<{url}|Query failed>:{query}")
    resp = "\n".join("".join(l) for l in result.l[:20])
    count = len(result.l)
    if count < 20:
        cstr = f'{count}'
    else:
        cstr = 'First 20'
    return {
        "text": f"<{result.url}|{cstr} results for `{query}`>.",
        "response_type": "in_channel",
        "attachments": [
            {
                "text":resp
            }
        ]
    }

def run_iterable(iterable, name, query):
    try:
        items = list(fn.take(20, iterable))
    except Exception as e:
        return dict(text=f"Query failed:{e}")
    print(items)
    resp = "\n".join("".join(l.val) for l in items[:20])
    count = len(items)
    if count < 20:
        cstr = f'{count}'
    else:
        cstr = 'First 20'
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
    def doit():
        requests.post(target, json=fn(*args))
    p = mp.Process(target=doit)
    p.start()
    return p

@app.route("/puzz", methods=["POST"])
def handle_cmd():
    query = request.form['text']
    target = request.form['response_url']
    cmd, rest = query.split(maxsplit=1)
    return fns[cmd](rest, target)

fns = {}

def method(name):
    def wrapper(fn):
        @app.route(f"/{name}", methods=["POST"], endpoint=name)
        def endpoint():
            query = request.form['text']
            target = request.form['response_url']
            return fn(query, target)
        fns[name] = fn
        return fn
    return wrapper

@method("qat")
def handle_qat(query, target):
    defer(run_service, target, qat, query)
    return jsonify({
        "text": "Asking qat to match `{}`...".format(query),
        "response_type": "in_channel",
    })

@method("nutr")
@method("nutrimatic")
def handle_nutr(query, target):
    defer(run_service, target, nutr, query)
    return jsonify({
        "text": "Asking Nutrimatic to match `{}`...".format(query),
        "response_type": "in_channel",
    })

@method("anagram")
@method("wordsmith")
def handle_anagram(query, target):
    defer(run_service, target, wordsmith, query)
    return jsonify({
        "text": "Finding anagrams for `{}`...".format(query),
        "response_type": "in_channel",
    })

@method("unphone")
def handle_unphone(query, target):
    defer(run_service, target, unphone, query)
    return jsonify({
        "text": "Finding phone matches for `{}`...".format(query),
        "response_type": "in_channel",
    })

def add_basic(name, fn):
    @method(name)
    def handle_it(query, target):
        text = str(fn(query))
        return jsonify(dict(
            text=text if text else "Nothing to do...",
            response_type = 'in_channel'))
    return handle_it

def braille(text):
    s = " A1B'K2L@CIF/MSP\"E3H9O6R^DJG>NTQ,*5<-U8V.%[$+X!&;:4\\0Z7(_?W]#Y)="
    return ''.join(chr(0x2800+s.index(t)) for t in text.upper() if t in s)

add_basic("morse", morse.encode)
add_basic("unmorse", morse.decode)
add_basic("nato", nato.encode)
add_basic("unnato", nato.decode)
add_basic("phone", to_phone)
add_basic('braille', braille)

if __name__ == '__main__':
    app.run()
