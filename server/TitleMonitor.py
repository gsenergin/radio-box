# -*- coding: utf-8 -*-

import urllib2
import threading, time
from Queue import Queue
from RadioBoxConstant import *

#number of second between each relaod of title
RELOAD_TIMEOUT = 20.0
class TitleMonitor(threading.Thread):
	def __init__(self, q):
		threading.Thread.__init__(self)
		self.shouldRun = True;
		self.q = q
		self.radio_name = ""
		self.nameQ = Queue()
		self.url = ""

	def run(self):
		print "start TM : " + self.radio_name
		u = None
		last_title = ""
		reload_timestamp = time.time()
		while self.shouldRun:
			if not self.nameQ.empty():
				#get last item
				while not self.nameQ.empty():
					self.radio_name = self.nameQ.get_nowait()
				#update url address
				'''if u != None:
					u.close()'''
				print "title url changed"
				if self.radio_name == "Sing Sing":
					self.url = 'http://www.sing-sing.org/programmation/'
					#this will trigger relaod
					reload_timestamp = 0
				elif self.radio_name == "France Inter":
					self.url = 'http://www.franceinter.fr'
					reload_timestamp = 0
				elif self.radio_name == "Radio Nova":
					self.url = 'http://www.novaplanet.com/cetaitquoicetitre/radionova'
					reload_timestamp = 0
				else:
					self.url = ""
					last_title = ""
					self.q.put_nowait("")
					time.sleep(0.01)
					continue
			if self.url != "" and (time.time() - reload_timestamp) > RELOAD_TIMEOUT:
				#print "TM do reload " + self.radio_name
				reload_timestamp = time.time()
				#fetch url target
				if u != None:
					u.close()
				try:
					u = urllib2.urlopen(self.url)
				except:
					continue
				data = u.read()
				#parse url and enqueue status if it has changed
				if self.radio_name == "Sing Sing":
					#find the first line (from the table title)
					ind = data.find("Artiste", 261)
					#artist
					ind = data.find("<font color=\"black\">", ind)
					ind = data.find("<font color=\"black\">", ind+1)
					title = data[ind + 20 : data.find("</font>", ind)]
					title += "/"
					ind = data.find("<font color=\"black\">", ind+1)
					title += data[ind + 20 : data.find("</font>", ind)]
				elif self.radio_name == "France Inter":
					ind = data.find("<a href=\"/player\" class=\"rf-player-open title\" title=\"Ecouter France Inter en direct\">")
					title = data[ind + 87 : data.find("</a>", ind) - 1]
					#title = title.decode('utf8').encode('ascii', 'ignore')
				elif self.radio_name == "Radio Nova":
					#find the first line (from the table title)
					#artist
					ind = data.find("<span id=\"artiste\">")
					title = strip_tags(data[ind + 19 : data.find("</span>", ind)])
					title += "/"
					ind = data.find("<span id=\"titre\">")
					title += data[ind + 17 : data.find("</span>", ind)]
				title = replace_non_ascii(title)
				if title != last_title:
					try:
						#give back the title to radioBox
						self.q.put_nowait(title)
						#print "sent"
						last_title = title
					except:
						pass
			else:
				#no url set
				time.sleep(0.01)
		if u != None:
			u.close()
		print "end TM"

	def update_name(self, name):
		self.nameQ.put_nowait(name)

	def stop(self):
		self.shouldRun = False
