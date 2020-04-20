#!/usr/bin/env python3

import configparser
from datetime import date, datetime, time
from email.message import EmailMessage
from smtplib import SMTP
from time import sleep
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

try:
    from pymongo import MongoClient
except:
    pass

config = configparser.ConfigParser(allow_no_value=True)
config.read('config.ini')

SUBSCRIBE = {
    'sender': config.get('email', 'SENDER'),
    'smtp_server': config.get('email', 'SMTP_SERVER'),
    'smtp_server_port': config.getint('email', 'SMTP_SERVER_PORT', fallback=587),
    'password': config.get('email', 'PWD'),
    'subscriber': config.get('email', 'SUBSCRIBER')
}

MONGO = {
    'server': config.get('mongodb', 'SERVER', fallback='localhost'),
    'port': config.getint('mongodb', 'PORT', fallback=27017),
    'database': config.get('mongodb', 'DATABASE', fallback='feh'),
    'collection': config.get('mongodb', 'COLLECTION', fallback='feh'),
    'username': config.get('mongodb', 'AUTH', fallback='feh'),
    'password': config.get('mongodb', 'PASSWORD', fallback='feh')
}


class EventNotOpen(Exception):
    pass


class FEH_VotingGauntlet:
    def __init__(self):
        self.date = datetime.combine(date.today(), time.min)
        self.hour = datetime.now().hour
        for _ in range(5):
            try:
                respone = requests.get(
                    'https://support.fire-emblem-heroes.com/voting_gauntlet/current', timeout=10)
                break
            except:
                respone = None
                sleep(5)
        if not respone:
            raise requests.exceptions.ReadTimeout
        self.current_event = int(respone.url.split('/')[-1])
        self.all_battles = BeautifulSoup(respone.content, 'html.parser').find_all(
            'li', class_='tournaments-battle')
        self.scoreboard = self.get_scoreboard()

    @staticmethod
    def get_round(battle):
        current = 0
        classes = battle.find_parent('article').find('h2')['class']
        for c in classes:
            if 'tournament' in c:
                current = c.split('-')[-1]
                break
        return int(current)

    def get_scoreboard(self):
        scoreboard = {}
        for battle in self.all_battles:
            Round = self.get_round(battle)
            try:
                scoreboard[Round]
            except KeyError:
                scoreboard[Round] = []
            content = [p.text for p in battle.find_all('p')]
            if content[1] == '':
                continue
            scoreboard[Round].append([
                {'hero': content[0], 'score':int(content[1].replace(',', ''))},
                {'hero': content[2], 'score':int(content[3].replace(',', ''))}
            ])
        return scoreboard

    @property
    def current_round(self):
        return max(self.scoreboard.keys())

    @property
    def current_scoreboard(self):
        scoreboard = self.scoreboard[self.current_round]
        if scoreboard == [] or [b for b in self.all_battles if 'win' not in str(b)] == []:
            raise EventNotOpen
        return scoreboard


def formatter(battle):
    hero1 = battle[0]['hero']
    score1 = battle[0]['score']
    hero2 = battle[1]['hero']
    score2 = battle[1]['score']
    return f"{hero1:　<8}{score1:>15,d}    VS    {hero2:　<8}{score2:>15,d}"


def mongo(feh: FEH_VotingGauntlet):
    try:
        from metadata import metadata
        MONGO = metadata('feh_mongo', ERROR_IF_NONE=True)
    except:
        pass
    if MONGO['auth']:
        username = quote_plus(MONGO['username'])
        password = quote_plus(MONGO['password'])
        URI = f"mongodb://{username}:{password}@{MONGO['server']}:{MONGO['port']}/{MONGO['database']}"
    else:
        URI = f"mongodb://{MONGO['server']}:{MONGO['port']}"
    try:
        with MongoClient(URI) as client:
            collection = client[MONGO['database']][MONGO['collection']]
            update = {'event': feh.current_event,
                      'date': feh.date, 'hour': feh.hour}
            all_scoreboard = feh.scoreboard
            for Round in all_scoreboard:
                update['round'] = Round
                for battle in all_scoreboard[Round]:
                    collection.update_one(
                        {'scoreboard': battle}, {'$setOnInsert': update}, True)
    except:
        pass


def mail(feh: FEH_VotingGauntlet):
    try:
        from metadata import metadata
        SUBSCRIBE = metadata('feh_subscribe', ERROR_IF_NONE=True)
    except:
        pass
    Round = {1: 'Round1', 2: 'Round2', 3: 'Final Round'}
    timestamp = f"{feh.date.strftime(f'%Y%m%d')} {feh.hour}:00:00"
    msg = EmailMessage()
    msg['Subject'] = f'FEH 投票大戦第{feh.current_event}回 {Round[feh.current_round]} - {timestamp}'
    msg['From'] = SUBSCRIBE['sender']
    msg['To'] = SUBSCRIBE['subscriber']
    content = '\n'.join([formatter(battle)
                         for battle in feh.current_scoreboard])
    msg.set_content(f'{content}\n\n{timestamp}')
    with SMTP(SUBSCRIBE['smtp_server'], SUBSCRIBE['smtp_server_port']) as s:
        s.starttls()
        s.login(SUBSCRIBE['sender'], SUBSCRIBE['password'])
        s.send_message(msg)


if __name__ == '__main__':
    try:
        feh = FEH_VotingGauntlet()
        mongo(feh)
        mail(feh)
    except EventNotOpen:
        pass
