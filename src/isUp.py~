'''
Created on May 29, 2011
@author: styles

sudo crontab -e
0 * * * * python /home/styles/Container/ChangeIP/src/isUp.py
'''
import subprocess
import smtplib
import datetime
import os
host = os.environ.get("DELL")
ping = subprocess.Popen(
    ["ping", "-c", "1", host],
    stdout = subprocess.PIPE,
    stderr = subprocess.PIPE
)
out, error = ping.communicate()
if out.find("Unreachable") > -1:
	mailserver = smtplib.SMTP('smtp.att.yahoo.com')
	mailserver.ehlo()
	mailserver.login("jason.heblack@sbcglobal.net", "hell123")
	mailserver.sendmail("jason.heblack@sbcglobal.net", ["jason.heblack@sbcglobal.net"], "Subject: DELL IS DOWN --- NOTICE dell is down --- notice")  
	mailserver.close()
else:
	filename = "/home/styles/Container/ChangeIP/src/isUp.log"
	file = open(filename, 'w')
	file.write(host + "is Up :-) "+str(datetime.datetime.today()))
	file.close()