#!/usr/bin/env python3

import configparser
from base64 import b64encode
from json import dumps
from sys import argv
from urllib.parse import quote_plus

import requests
from pymongo import MongoClient

config = configparser.ConfigParser(allow_no_value=True)
config.read('config.ini')

MONGO = {
    'server': config.get('mongodb', 'SERVER', fallback='localhost'),
    'port': config.getint('mongodb', 'PORT', fallback=27017),
    'database': config.get('mongodb', 'DATABASE', fallback='feh'),
    'collection': config.get('mongodb', 'COLLECTION', fallback='feh'),
    'username': config.get('mongodb', 'AUTH'),
    'password': config.get('mongodb', 'PASSWORD')
}

GITHUB = {
    'token': config.get('github', 'TOKEN'),
    'user': config.get('github', 'USER'),
    'repo': config.get('github', 'REPO'),
    'path': config.get('github', 'PATH')
}

PROXY = config.get('proxy', 'PROXY')


def query(filter_or_pipeline=None, projection=None, sort=None, limit=0, mode='find'):
    try:
        from metadata import metadata
        MONGO = metadata('feh_mongo', ERROR_IF_NONE=True)
    except:
        pass
    if MONGO['username']:
        username = quote_plus(MONGO['username'])
        password = quote_plus(MONGO['password'])
        URI = f"mongodb://{username}:{password}@{MONGO['server']}:{MONGO['port']}/{MONGO['database']}"
    else:
        URI = f"mongodb://{MONGO['server']}:{MONGO['port']}"
    with MongoClient(URI) as client:
        if mode == 'find':
            return list(client[MONGO['database']][MONGO['collection']].find(filter_or_pipeline, projection, sort=sort, limit=limit))
        else:
            return list(client[MONGO['database']][MONGO['collection']].aggregate(filter_or_pipeline))


def commit(name, content):
    try:
        from metadata import metadata
        GITHUB = metadata('feh_github', ERROR_IF_NONE=True)
    except:
        pass
    url = f"https://api.github.com/repos/{GITHUB['user']}/{GITHUB['repo']}/contents/{GITHUB['path']}/{name}.json"
    data = {'message': name, 'content': content}
    headers = {'Authorization': f"token {GITHUB['token']}"}
    if PROXY:
        proxies = {'https': f'http://{PROXY}'}
    else:
        proxies = None
    return requests.put(url, json=data, headers=headers, proxies=proxies, timeout=10)


def converter(jsonlist):
    output = '['
    i = 1
    for json in jsonlist:
        try:
            json['date'] = str(json['date'].date())
        except KeyError:
            pass
        output += dumps(json, ensure_ascii=False)
        if i < len(jsonlist):
            output += ',\n'
        i += 1
    output += ']'
    return b64encode(output.encode()).decode()


if __name__ == '__main__':
    if len(argv) > 1:
        try:
            event = int(argv[1])
            if query({'event': event}) == []:
                raise ValueError('No results.')
        except:
            print('[Warning!]Invalid argument or no results. Use last result instead.')
            event = query(None, {'event': 1}, [('event', -1)], 1)[0]['event']
    else:
        event = query(None, {'event': 1}, [('event', -1)], 1)[0]['event']
    name = f'FEH 投票大戦第{event}回'
    data = query({'event': event}, {'_id': 0, 'event': 0},
                 [('round', 1), ('scoreboard', 1), ('date', 1), ('hour', 1)])
    respone = commit(name, converter(data))
    if respone.status_code == 201:
        print(f'{name}.json uploaded.')
    else:
        print(f'Upload {name}.json failed!\n')
        print(respone.json()['message'])
    name = f'FEH 投票大戦第{event}回結果一覧'
    pipeline = []
    pipeline.append({'$addFields': {'tmp': '$scoreboard'}})
    pipeline.append({'$unwind': '$tmp'})
    pipeline.append({'$group': {'_id': {'r': '$round', 'h': '$tmp.hero'},
                                's': {'$max': '$scoreboard'}, 'd': {'$max': '$date'}}})
    pipeline.append(
        {'$group': {'_id': {'d': '$d', 'r': '$_id.r', 's': '$s'}}})
    pipeline.append(
        {'$project': {'_id': 0, 'date': '$_id.d', 'round': '$_id.r', 'scoreboard': '$_id.s'}})
    pipeline.append({'$sort': {'round': 1, 'scoreboard': 1}})
    data = query(pipeline, mode='aggregate')
    respone = commit(name, converter(data))
    if respone.status_code == 201:
        print(f'{name}.json uploaded.')
    else:
        print(f'Upload {name}.json failed!\n')
        print(respone.json()['message'])
