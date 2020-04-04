#!/usr/bin/env python3

import smtplib
from datetime import datetime
from email.message import EmailMessage
from time import sleep

import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient

SENDER = ''  # sender mail address
SMTP_SERVER = ''  # sender smtp server
SMTP_SERVER_PORT = 587  # sender smtp server port
PWD = ''  # sender auth password
SUBSCRIBER = ''  # subscriber mail address

MONGO_SERVER = 'localhost'  # mongodb server address
MONGO_PORT = 27017  # mongodb server port
MONGO_DATABASE = 'feh'  # mongodb database
MONGO_COLLECTION = 'feh'  # mongodb collection
MONGO_AUTH = None  # mongodb auth username
MONGO_PASSWORD = None  # mongodb auth password


class EventNotOpen(Exception):
    pass


class FEH_VotingGauntlet:
    def __init__(self):
        self.date = datetime.now()
        self.hour = str(datetime.now().hour)
        self.timestamp = f"{self.date.strftime(f'%Y%m%d')} {self.hour}:00:00"
        respone = requests.get(
            'https://support.fire-emblem-heroes.com/voting_gauntlet/current')
        self.current_event = respone.url.split('/')[-1]
        all_battles = BeautifulSoup(respone.content, 'html.parser').find_all(
            'li', class_='tournaments-battle')
        self.current_battles = [
            battle for battle in all_battles if 'win' not in str(battle)]
        if self.current_battles == []:
            raise EventNotOpen

    @property
    def current_round(self):
        classes = self.current_battles[0].find_parent(
            'article').find('h2')['class']
        for c in classes:
            if 'tournament' in c:
                current = c.split('-')[-1]
                break
        return str(int(current))

    @property
    def current_scoreboard(self):
        scoreboard = []
        for battle in self.current_battles:
            content = [p.text for p in battle.find_all('p')]
            if content[1] == '':
                raise EventNotOpen
            scoreboard.append([
                {'hero': content[0], 'score':int(content[1].replace(',', ''))},
                {'hero': content[2], 'score':int(content[3].replace(',', ''))}
            ])
        return scoreboard


def formatter(battle):
    return f"{battle[0]['hero']:　<8}{battle[0]['score']:>15,d}    VS    {battle[1]['hero']:　<8}{battle[1]['score']:>15,d}"


def mongo(feh: FEH_VotingGauntlet):
    try:
        with MongoClient(MONGO_SERVER, MONGO_PORT, username=MONGO_AUTH, password=MONGO_PASSWORD) as client:
            collection = client[MONGO_DATABASE][MONGO_COLLECTION]
            update = {'event': feh.current_event, 'round': feh.current_round,
                      'date': feh.date.strftime(f'%Y-%m-%d'), 'hour': feh.hour}
            for battle in feh.current_scoreboard:
                collection.update_one(
                    {'scoreboard': battle}, {'$set': update}, True)
    except:
        pass


def mail(feh: FEH_VotingGauntlet):
    Round = {'1': 'Round1', '2': 'Round2', '3': 'Final Round'}
    msg = EmailMessage()
    msg['Subject'] = f'FEH 投票大戦第{feh.current_event}回 {Round[feh.current_round]} - {feh.timestamp}'
    msg['From'] = SENDER
    msg['To'] = SUBSCRIBER
    content = '\n'.join([formatter(battle)
                         for battle in feh.current_scoreboard])
    msg.set_content(f'{content}\n\n{feh.timestamp}')
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
