# FEH_VotingGauntlet

Python script that mail current Fire Emblem Hero Voting Gauntlet event scoreboard and record scoreboard into mongodb.

Before use, you must config sender and subscriber mail account.

## Requirements
Package used that are not present in the Python Standard Library
- `requests`
- `BeautifulSoup`
- `pymongo`

It is recommended to add a cron job or a scheduled task to run every hour.
