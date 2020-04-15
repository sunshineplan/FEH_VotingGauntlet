#!/usr/bin/env python3

import configparser
from datetime import datetime
from email.message import EmailMessage
from io import BytesIO
from smtplib import SMTP
from subprocess import check_output

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

if __name__ == '__main__':
    command = f'mongodump -h{MONGO_SERVER}:{MONGO_PORT} -d{MONGO_DATABASE} -c{MONGO_COLLECTION} -u{MONGO_AUTH} -p{MONGO_PASSWORD} --gzip --archive'
    attachment = BytesIO()
    attachment.write(check_output(command, shell=True))
    msg = EmailMessage()
    msg['Subject'] = f'FEH Backup-{datetime.now():%Y%m%d}'
    msg['From'] = SENDER
    msg['To'] = SUBSCRIBER
    msg.add_attachment(attachment.getvalue(), maintype='application',
                       subtype='octet-stream', filename='database')
    with SMTP(SMTP_SERVER, SMTP_SERVER_PORT) as s:
        s.starttls()
        s.login(SENDER, PWD)
        s.send_message(msg)
    print('Backup FEH done.')
