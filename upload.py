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

MONGO_SERVER = config.get('mongodb', 'SERVER', fallback='localhost')
MONGO_PORT = config.getint('mongodb', 'PORT', fallback=27017)
MONGO_DATABASE = config.get('mongodb', 'DATABASE', fallback='feh')
MONGO_COLLECTION = config.get('mongodb', 'COLLECTION', fallback='feh')
MONGO_AUTH = config.get('mongodb', 'AUTH')
MONGO_PASSWORD = config.get('mongodb', 'PASSWORD')

GITHUB_TOKEN = config.get('github', 'TOKEN')
GITHUB_USER = config.get('github', 'USER')
GITHUB_REPO = config.get('github', 'REPO')
PATH = config.get('github', 'PATH')
PROXY = config.get('github', 'PROXY')


def query(filter_or_pipeline=None, projection=None, sort=None, limit=0, mode='find'):
    if MONGO_AUTH:
        username = quote_plus(MONGO_AUTH)
        password = quote_plus(MONGO_PASSWORD)
        URI = f"mongodb://{username}:{password}@{MONGO_SERVER}:{MONGO_PORT}/{MONGO_DATABASE}"
    else:
        URI = f'mongodb://{MONGO_SERVER}:{MONGO_PORT}'
    with MongoClient(URI) as client:
        if mode == 'find':
            return list(client[MONGO_DATABASE][MONGO_COLLECTION].find(filter_or_pipeline, projection, sort=sort, limit=limit))
        else:
            return list(client[MONGO_DATABASE][MONGO_COLLECTION].aggregate(filter_or_pipeline))


def commit(name, content):
    url = f'https://api.github.com/repos/{GITHUB_USER}/{GITHUB_REPO}/contents/{PATH}/{name}.json'
    data = {'message': name, 'content': content}
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}
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
                                's': {'$max': '$scoreboard'}}})
    pipeline.append({'$group': {'_id': {'r': '$_id.r', 's': '$s'}}})
    pipeline.append(
        {'$project': {'_id': 0, 'round': '$_id.r', 'scoreboard': '$_id.s'}})
    pipeline.append({'$sort': {'round': 1, 'scoreboard': 1}})
    data = query(pipeline, mode='aggregate')
    respone = commit(name, converter(data))
    if respone.status_code == 201:
        print(f'{name}.json uploaded.')
    else:
        print(f'Upload {name}.json failed!\n')
        print(respone.json()['message'])
