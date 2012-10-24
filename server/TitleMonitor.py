# -*- coding: utf-8 -*-

import urllib2
import threading, time
from Queue import Queue
from RadioBoxConstant import *

#number of second between each relaod of title
#RELOAD_TIMEOUT = 20.0
RELOAD_TIMEOUT = 20

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
				if self.radio_name == "Sing Sing":
					self.url = 'http://www.sing-sing.org/programmation/'
					reload_timestamp = 0
				elif self.radio_name == "France Inter":
					self.url = 'http://www.franceinter.fr'
					reload_timestamp = 0
				elif self.radio_name == "Radio Nova":
					#self.url = 'http://www.novaplanet.com/cetaitquoicetitre/radionova'
					self.url = 'http://www.novaplanet.com/radionova/cetaitquoicetitre'
					reload_timestamp = 0
				else:
					self.url = ""
					last_title = ""
					self.q.put_nowait("")
					time.sleep(0.1)
					continue
			if self.url != "" and (time.time() - reload_timestamp) > RELOAD_TIMEOUT:
				reload_timestamp = time.time()
				#fetch url target
				if u != None:
					#TODO close after reading !!!
					u.close()
				try:
					#u = urllib2.urlopen(self.url)
					#debug
					#hdrs = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:16.0) Gecko/20100101 Firefox/16.0', 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Cache-Control': 'max-age=0', 'Connection': 'keep-alive', 'Cookie': 'OAX=VNd0XVB51pkACxVW; RMFD=011TNCdqK60NASc; __utma=9893290.1005282376.1350162074.1350176706.1350223898.3; __utmz=9893290.1350162074.1.1.utmcsr=google|utmccn=(organic)|utmcmd=organic|utmctr=(not%20provided); __utmb=9893290.5.10.1350223898; __utmc=9893290', 'DNT': '1'}
					if self.radio_name == "Radio Nova":
						#not sure which are usefull, but without Cookie, the page is never reloaded
						hdrs = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:16.0) Gecko/20100101 Firefox/16.0', 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8', 'Cache-Control': 'max-age=0', 'Connection': 'keep-alive', 'Cookie': 'OAX=VNd0XVB51pkACxVW; RMFD=011TNCdqK60NASc; __utma=9893290.1005282376.1350162074.1350176706.1350223898.3; __utmz=9893290.1350162074.1.1.utmcsr=google|utmccn=(organic)|utmcmd=organic|utmctr=(not%20provided); __utmb=9893290.5.10.1350223898; __utmc=9893290', 'DNT': '1'}  
						request = urllib2.Request(url = self.url, headers = hdrs)
						u = urllib2.urlopen(request)
					else:
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
				elif self.radio_name == "Radio Nova":
					#find the first line (from the table title)
					#artist
					ind = data.find("<h2 class=\"artiste\">")
					title = strip_tags(data[ind + 21 : data.find("</h2>", ind)])
					#remove space/tab etc
					title = ' '.join(title.split())
					title += "/"
					ind = data.find("<h3 class=\"titre\">")
					title += data[ind + 18 : data.find("</span>", ind)]
				title = replace_non_ascii(title)
				if u != None:
					#TODO close after reading !!!
					u.close()
				if title != last_title:
					try:
						#give back the title to radioBox
						self.q.put_nowait(title)
						last_title = title
					except:
						pass
			else:
				#no url set
				time.sleep(1.0)
		if u != None:
			u.close()
		print "end TM"

	def update_name(self, name):
		self.nameQ.put_nowait(name)

	def stop(self):
		self.shouldRun = False
