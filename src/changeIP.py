import sys
from com.gargoylesoftware.htmlunit import NicelyResynchronizingAjaxController
from com.gargoylesoftware.htmlunit import WebClient
from java.util import logging
from org.apache.commons.logging import LogFactory
import telnetlib
import datetime
import dateutil.parser
import smtplib
import subprocess
import traceback
import fileinput
import shutil
###########################################################################
'''
The script is meant to be called from a cron job run every few hours or so. 
The current ip must be set in (the file of) THE_IP_FILE, before this program 
is ever run for the first time and ...THE_IP_FILE must always exist on each 
run. THE_IP_FILE contains the ip that was previously set at the registrar. 

The program telnets to the router to obtain the current ip of the system. 
After that, it checks the old value stored in THE_IP_FILE. If the current 
(new) ip is different than what was stored, then the program will modify
local BIND files to reflect the change, restart BIND, and then update the 
DNS registry (online) to have the name server for this domain (in the 
registrar) point to the new ip of the local BIND servers.

Any Exception (network, file-io, etc..) that occurs will hopefully be logged 
and trigger an email message to an admin.. When the BIND ip is changed by this
program, then also an email will be sent to an admin..

1. run script as root
Notes: Serial in BIND_DATA file must be set as a date in YYYYMMDD format!!!
The Bind Configuration files should all be backed-up before this is ever
run!!!

sudo jython -Dpython.path="/home/styles/Installed/htmlunit-2.8/lib/httpclient-4.0.1.jar:/home/styles/Installed/htmlunit-2.8/lib/commons-collections-3.2.1.jar:/home/styles/Installed/htmlunit-2.8/lib/cssparser-0.9.5.jar:/home/styles/Installed/htmlunit-2.8/lib/httpcore-4.0.1.jar:/home/styles/Installed/htmlunit-2.8/lib/httpmime-4.0.1.jar:/home/styles/Installed/htmlunit-2.8/lib/apache-mime4j-0.6.jar:/home/styles/Installed/htmlunit-2.8/lib/commons-io-1.4.jar:/home/styles/Installed/htmlunit-2.8/lib/sac-1.3.jar:/home/styles/Installed/htmlunit-2.8/lib/nekohtml-1.9.14.jar:/home/styles/Installed/htmlunit-2.8/lib/xalan-2.7.1.jar:/home/styles/Installed/htmlunit-2.8/lib/serializer-2.7.1.jar:/home/styles/Installed/htmlunit-2.8/lib/commons-logging-1.1.1.jar:/home/styles/Installed/htmlunit-2.8/lib/xml-apis-1.3.04.jar:/home/styles/Installed/htmlunit-2.8/lib/commons-codec-1.4.jar:/home/styles/Installed/htmlunit-2.8/lib/xercesImpl-2.9.1.jar:/home/styles/Installed/htmlunit-2.8/lib/htmlunit-2.8.jar:/home/styles/Installed/htmlunit-2.8/lib/commons-lang-2.4.jar:/home/styles/Installed/htmlunit-2.8/lib/htmlunit-core-js-2.8.jar:/usr/share/pyshared" changeIP.py


'''
############################################################################
CONTACT_EMAIL="jason.heblack@sbcglobal.net"
#router telnet info...
HOST = "192.168.1.1"
PASSWORD = "chdabbr0"
USER = "admin"
DISPLAY_IP="ifconfig\n"
IP_START_LINE="eth2.2"
IP_START_TOKEN="inet addr:"
#BIND9 (nameserver) and script config. files...
#
#All files must be present at all times!
#No file here should be modified by another process
#while this script is being run since it does not
#lock files to prevent that use case scenario. Note:
#can use lockfile module at a later time to cover it.
BIND_DIR=""
BIND_ZONES=BIND_DIR+"named.conf.local"
BIND_DATA=BIND_DIR+"db.thesame"
THE_IP_FILE=BIND_DIR+"changeIP.ip"
IP_LOG_FILE=BIND_DIR+"changeIP.log"
SENDEMAIL_BIT=BIND_DIR+"changeIP.bit"
#domain info...
REGISTRARS_LOGIN_PAGE="http://namebargain.com/domain-tools/name-servers.aspx"
NAME_SERVER="ns.thesame.net"
############################################################################
def validIP(address):
	parts = address.split(".")
	if len(parts) != 4:
		return False
	try:
		for item in parts:
			if not 0 <= int(item) <= 255:
				return False
		return True
	except ValueError:
		return False
############################################################################
def quitlog(msg):
	global file
	#if an exption happens here on the file activity, then this is the only
	#place where the program would break and no one would know... look into
	#what happens when the program has an unrecoverable exception. Can 
	#
	if file!=None and not file.closed:
		file.close()
	file = open(IP_LOG_FILE,'a')
	file.write("*** "+str(datetime.date.today())+ " DETAIL: "+ traceback.format_exc() + str(msg) + "\n")
	file.write("-----------------------------------------------------------------------------\n")
	file.close()
	#Set (failsafe) bit to TRUE in SENDEMAIL_BIT to indicate an email should	
	#be sent. If there is a problem that blocked the email from being sent, 
	#then the bit will remain as a "1" to indicate that an email still 
	#needs to be sent out... At script start, script always trys to clear
	#that one out.
	file = open(SENDEMAIL_BIT,'w')
	file.write("1");
	file.close();
	#send email...
	sendemail()
	sys.exit(1)
############################################################################
def sendemail():
	#check if set to send email...
	try:
		file=None #in case of exception, init to None
		file=open(SENDEMAIL_BIT,'r')
		bit=file.read(1);
		file.close();
		if bit != "1":
			return	#bit was previously set to '0', skip sending email... 
						#any problem had been cleared
	except IOError:
		if file!=None:
			file.close();
		return    #return if SENDEMAIL_BIT file doesn't exist
	sender = CONTACT_EMAIL
	receivers = [CONTACT_EMAIL]
	message = """Subject: /ETC/BIND/CHANGEIP.LOG --- NOTICE
	/etc/bind/changeIP.log --- notice
	"""
	try:
		mailserver = smtplib.SMTP('smtp.att.yahoo.com')
		mailserver.ehlo()
		mailserver.starttls()
		mailserver.ehlo()
		mailserver.login(CONTACT_EMAIL, "hell123")
		mailserver.sendmail(sender, receivers, message)  
		mailserver.close()       
	except Exception, err:
		file = open(IP_LOG_FILE,'a')
		file.write("*** "+str(datetime.date.today())+ " ERROR: " + traceback.format_exc() + str(err) + "\n")
		file.write("-----------------------------------------------------------------------------\n")
		file.close()		
		return
	#successful, clear to prevent email from automatically being sent next time
	file = open(SENDEMAIL_BIT,'w')
	file.write("0");
	file.close();	
############################################################################	
############################################################################
############################################################################
sendemail()#try to send out any warning that did not go out the last time...
try:
	####################################telnet to router
	telnet = telnetlib.Telnet(HOST)
	telnet.read_until("login: ")
	telnet.write(USER + "\n")
	telnet.read_until("Password: ")
	telnet.write(PASSWORD + "\n")
	####################################get ip
	telnet.write(DISPLAY_IP)
	telnet.write("exit\n")	
	string = telnet.read_all()
	pos = string.find(IP_START_LINE)
	ipMissing=False
	if pos==-1:
		ipMissing=True
	else:
		pos = string.find(IP_START_TOKEN,pos)	
		if pos==-1:
			ipMissing=True
		else:
			posend = string.find(" ",pos+len(IP_START_TOKEN))
			currentip=string[pos+len(IP_START_TOKEN):posend]		
	if ipMissing or not validIP(currentip):
		quitlog("ip not found... ipMissing: "+str(ipMissing) + " currentip: " + currentip + " TELNETED???") #exit...
	else:
		#########################check that ip is same as in the file
		file=None
		file = open(THE_IP_FILE,'r')
		savedip=file.readline()
		file.close()
		if savedip == currentip:
			sys.exit(0) #ips are the same, no problems... exit
	############################ips ARE NOT the same if made it past this point...-
	###################
	###################change ip/serial in BIND config files
	try:
		for line in fileinput.input (BIND_DATA, inplace=1):
			tokens=line.split()
			if len(tokens)>1 and tokens[0]=="ns" and tokens[1]=="IN" and tokens[2]=="A":
				#ip
				sys.stdout.write("ns\t\t\t\t\tIN\t\tA\t\t"+currentip+"\n")
			elif len(tokens)>1 and tokens[1]==";" and tokens[2]=="Serial":
				today=datetime.date.today()
				#serial
				serial=dateutil.parser.parse(tokens[0],fuzzy=True).date()
				#increase by a day
				if serial < today:
					serial=today
				elif serial == today:
					serial = today + datetime.timedelta(days=1)
				else:
					serial = serial + datetime.timedelta(days=1)
				if serial.month < 10:
					month="0"+str(serial.month)
				else:
					month=str(serial.month)
				if serial.day < 10:
					day="0"+str(serial.day)
				else:
					day=str(serial.day)
				sys.stdout.write("\t\t\t\t\t\t\t" + str(serial.year)+month+day+"\t\t; Serial\n")
			else:
				sys.stdout.write(line)
	except IOError, err:
		if fileinput.fileno() != -1: #file was opened
			#write the backup back to original
			shutil.copy(fileinput.filename()+".bak",fileinput.filename())
			#close the open file
			fileinput.close()
		#redirect stdout from file 
		sys.stdout = sys.__stdout__
		quitlog(err)
	#change ZONE for the ip
	try:
		for line in fileinput.input(BIND_ZONES, inplace=1):	#is not localhost entry, then assume the
			if line.find("in-addr.arpa")!=-1:						#in-addr.arpa entry found is that which
				if line.find("0.0.127.in-addr.arpa")==-1:			#corresponds to our ip
					tokens=currentip.split(".")							
					sys.stdout.write("zone \""+tokens[2] + "." + tokens[1] + "." + tokens[0] + ".in-addr.arpa\" {\n")
					continue													
			sys.stdout.write(line)
	except IOError, err:
		if fileinput.fileno() != -1: #file was opened
			#write the backup back to original
			shutil.copy(fileinput.filename()+".bak",fileinput.filename())
			#close the open file
			fileinput.close()
		#redirect stdout from file 
		sys.stdout = sys.__stdout__	
		quitlog(err)	
	#restart bind9
	retcode = subprocess.call(["service", "bind9" ,"restart"])
	if retcode != 0:
		quitlog("error restarting bind9...")
	#	
	#now go to DNS registrar and update ip for nameserver there
	logger = LogFactory.getLog('com.gargoylesoftware.htmlunit')
	logger.getLogger().setLevel(logging.Level.OFF) 
	#browser
	webClient = WebClient()
	webClient.setCssEnabled(False)
	webClient.setJavaScriptEnabled(True)
	webClient.setAjaxController(NicelyResynchronizingAjaxController()) #will tell your WebClient instance to re-synchronize asynchronous XHR.
	#login to the url
	page = webClient.getPage(REGISTRARS_LOGIN_PAGE)
	login = page.getElementById("ctl00_cph_content_txtUsername")
	login.setValueAttribute("OURRUN")
	password = page.getElementById("ctl00_cph_content_txtPassword")
	password.setValueAttribute("GREASE")
	submit = page.getElementById("ctl00_cph_content_btnLogin")
	#ip settings sheet
	sheet = submit.click()
	nameserver=sheet.getElementById("ctl00_cph_content_tbUpdateNsName")
	nameserver.setValueAttribute(NAME_SERVER)
	oldip = sheet.getElementById("ctl00_cph_content_tbUpdateNsOldIP")
	oldip.setValueAttribute(savedip)
	newip = sheet.getElementById("ctl00_cph_content_tbUpdateNsNewIP")
	newip.setValueAttribute(currentip)
	submit = sheet.getElementById("ctl00_cph_content_btnUpdate")
	#submit new ip
	page = submit.click()
	webClient.closeAllWindows();
	#update ip on file with current ip
	file=None
	file = open(THE_IP_FILE,'w')
	file.write(currentip)
	file.close()
	quitlog("ChangedIP: " + currentip + " !!!")
except Exception, err:
	quitlog(err)