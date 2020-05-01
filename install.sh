#! /bin/bash

installSoftware() {
    apt -qq -y install python3-pymongo python3-requests python3-bs4
}

installFEH() {
    curl -Lo- https://github.com/sunshineplan/FEH_VotingGauntlet/archive/v1.0.tar.gz | tar zxC /etc
    mv /etc/FEH_VotingGauntlet* /etc/feh
    chmod +x /etc/feh/*.py
}

createCronTask() {
    cp -s /etc/feh/feh.cron /etc/cron.d/feh
    chmod 644 /etc/feh/feh.cron
}

main() {
    installSoftware
    installFEH
    createCronTask
}

main
