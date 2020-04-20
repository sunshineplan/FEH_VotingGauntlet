#!/usr/bin/env python3

import configparser
from datetime import datetime
from email.message import EmailMessage
from io import BytesIO
from smtplib import SMTP
from subprocess import check_output

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


if __name__ == '__main__':
    try:
        from metadata import metadata
        SUBSCRIBE = metadata('feh_subscribe', ERROR_IF_NONE=True)
        MONGO = metadata('feh_mongo', ERROR_IF_NONE=True)
    except:
        pass
    command = f"mongodump -h{MONGO['server']}:{MONGO['port']} -d{MONGO['database']} -c{MONGO['collection']} -u{MONGO['username']} -p{MONGO['password']} --gzip --archive"
    attachment = BytesIO()
    attachment.write(check_output(command, shell=True))
    msg = EmailMessage()
    msg['Subject'] = f'FEH Backup-{datetime.now():%Y%m%d}'
    msg['From'] = SUBSCRIBE['sender']
    msg['To'] = SUBSCRIBE['subscriber']
    msg.add_attachment(attachment.getvalue(), maintype='application',
                       subtype='octet-stream', filename='database')
    with SMTP(SUBSCRIBE['smtp_server'], SUBSCRIBE['smtp_server_port']) as s:
        s.starttls()
        s.login(SUBSCRIBE['sender'], SUBSCRIBE['password'])
        s.send_message(msg)
    print('Backup FEH done.')
