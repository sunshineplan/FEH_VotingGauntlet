#!/usr/bin/env python3

import configparser
import smtplib
from datetime import date, datetime, time
from email.message import EmailMessage
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

SENDER = config.get('email', 'SENDER')
SMTP_SERVER = config.get('email', 'SMTP_SERVER')
SMTP_SERVER_PORT = config.getint('email', 'SMTP_SERVER_PORT', fallback=587)
PWD = config.get('email', 'PWD')
SUBSCRIBER = config.get('email', 'SUBSCRIBER')

MONGO_SERVER = config.get('mongodb', 'SERVER', fallback='localhost')
MONGO_PORT = config.getint('mongodb', 'PORT', fallback=27017)
MONGO_DATABASE = config.get('mongodb', 'DATABASE', fallback='feh')
MONGO_COLLECTION = config.get('mongodb', 'COLLECTION', fallback='feh')
MONGO_AUTH = config.get('mongodb', 'AUTH')
MONGO_PASSWORD = config.get('mongodb', 'PASSWORD')


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
    if MONGO_AUTH:
        username = quote_plus(MONGO_AUTH)
        password = quote_plus(MONGO_PASSWORD)
        URI = f"mongodb://{username}:{password}@{MONGO_SERVER}:{MONGO_PORT}/{MONGO_DATABASE}"
    else:
        URI = f'mongodb://{MONGO_SERVER}:{MONGO_PORT}'
    try:
        with MongoClient(URI) as client:
            collection = client[MONGO_DATABASE][MONGO_COLLECTION]
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
    Round = {1: 'Round1', 2: 'Round2', 3: 'Final Round'}
    timestamp = f"{feh.date.strftime(f'%Y%m%d')} {feh.hour}:00:00"
    msg = EmailMessage()
    msg['Subject'] = f'FEH 投票大戦第{feh.current_event}回 {Round[feh.current_round]} - {timestamp}'
    msg['From'] = SENDER
    msg['To'] = SUBSCRIBER
    content = '\n'.join([formatter(battle)
                         for battle in feh.current_scoreboard])
    msg.set_content(f'{content}\n\n{timestamp}')
    with smtplib.SMTP(SMTP_SERVER, SMTP_SERVER_PORT) as s:
        s.starttls()
        s.login(SENDER, PWD)
        s.send_message(msg)


if __name__ == '__main__':
    try:
        feh = FEH_VotingGauntlet()
        mongo(feh)
        mail(feh)
    except EventNotOpen:
        pass
