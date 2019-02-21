Manage running processes

Reset the daemon for luigi
ps ax | luigid
sudo kill xxxx

sudo python3 /usr/local/bin/luigid --background


Reset the api
ps ax | application.py
sudo kill xxxx
./app.sh

Change the timing of the hourly luigi runs
crontab -e 
