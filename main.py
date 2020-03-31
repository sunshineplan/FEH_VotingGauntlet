#!/usr/bin/env python3

import datetime
import smtplib
import time
from email.message import EmailMessage

import requests
from bs4 import BeautifulSoup

SENDER = '' # sender mail address
SMTP_SERVER = '' #sender smtp server
SMTP_SERVER_PORT = 587 #sender smtp server port
PWD = '' # sender auth password
SUBSCRIBER = '' # subscriber mail address


class EventNotOpen(Exception):
    pass


class FEH_VotingGauntlet:
    def __init__(self):
        self.timestamp = datetime.datetime.now().strftime('%Y%m%d %H:00:00')
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
        Round = {'01': 'Round1', '02': 'Round2', '03': 'Final Round'}
        return Round[current]

    @property
    def current_situation(self):
        situation = []
        for battle in self.current_battles:
            content = [p.text for p in battle.find_all('p')]
            if content[1] == '':
                raise EventNotOpen
            situation.append(
                f'{content[0]:　<8}{content[1]:>15}    VS    {content[2]:　<8}{content[3]:>15}')
        return '\n'.join(situation)


def emailResult(feh: FEH_VotingGauntlet):
    msg = EmailMessage()
    msg['Subject'] = f'FEH 投票大戦第{feh.current_event}回 {feh.current_round} - {feh.timestamp}'
    msg['From'] = SENDER
    msg['To'] = SUBSCRIBER
    content = F'{feh.current_situation}\n\n{feh.timestamp}'
    msg.set_content(content)
    with smtplib.SMTP(SMTP_SERVER, SMTP_SERVER_PORT) as s:
        s.starttls()
        s.login(SENDER, PWD)
        s.send_message(msg)


if __name__ == '__main__':
    try:
        emailResult(FEH_VotingGauntlet())
    except EventNotOpen:
        pass
