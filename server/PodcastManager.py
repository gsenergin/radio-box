#!/usr/bin/python

import threading, time, string, os, fileinput, urllib
from RadioBoxConstant import *
from subprocess import Popen, PIPE
from dateutil.parser import parse
from Queue import Queue, Empty

#minimum time in sec between 2 podcast updates : 30min
MIN_TIME_BEFOR_UPDATE = 1800

class PodcastManager(threading.Thread):
	last_update = 0

	def __init__(self):
		threading.Thread.__init__(self)
		self.channels = []
		self.do_update = False
		self.dlQ = Queue()

	def run(self):
		self.shouldRun = True
		self.last_update = 0
		while self.shouldRun:
			if self.do_update:
				try:
					#get list of podcats
					os.chdir(HOME_DIR)
					#one directory, one channel
					tmp = []
					for d in os.listdir('./podcast'):
						print "Channel : ", d
						c = Channel(d)
						#ignore Channel with no episodes
						if len(c.episodes) != 0:
							tmp.append(c)
					self.channels = tmp
					self.do_update = False
				except e:
					self.do_update = False
					print "Error while updating podcast"
					print e
			elif not self.dlQ.empty():
				try:
					e = self.dlQ.get_nowait()
					e.download()
				except e:
					print "Error while downloading episode"
					print e
			else:
				time.sleep(0.1)
			#break

	def stop(self):
		self.shouldRun = False

	def update(self, wait=False, timeout=20.0):
		#set flag for PodcastManager thread to do the update
		self.do_update = True
		t = time.time()
		#wait for update to complete (if option was set)
		while self.do_update and wait and (time.time() - t) < timeout:
			time.sleep(0.1);

	def download(self, episode):
		#THIS TODO For sure !!! pouet pouet
		#start new thread using worker = Thread(target=Watchdog.read_pipe, args=(self, q, p)) ??
		#self.dlQ.put_nowait(episode)
		pass
	def play_episode(self, episode):
		pass

	def get_channel_list(self):
		return self.channels

class Channel():
	def __init__(self, name):
		self.name = name
		self.episodes = []
		self.reload_episodes()

	def reload_episodes(self):
		##extract episode list from internet or local cache
		#from the net
		if not os.path.isfile(HOME_DIR+'/podcast/'+self.name+'/url'):
			print "no url specified, ignoring this channel"
			return
		#fetch from the net, only if is has not been done the last MIN_TIME_BEFORE_UPDATE
		if time.time() - PodcastManager.last_update > MIN_TIME_BEFORE_UPDATE:
			print "update channel form net"
			for line in fileinput.input(HOME_DIR+'/podcast/'+self.name+'/url'):
				#print "xsltproc ", XSLT_PARSE, " ", line[:-1]
				p = Popen(["xsltproc", XSLT_PARSE, line[:-1]], stdout=PIPE)
				while p.poll() == None:
					time.sleep(0.1)
				l = p.stdout.readline()
				while len(l) != 0:
					self.episodes.append(Episode(self.name, l))
					l = p.stdout.readline()
				#print len(self.episodes)
			fileinput.close()
			PodcastManager.last_update = time.time()
			self.update_local_cache()
		else:
			#from the local cache
			if os.path.exists(HOME_DIR+'/podcast/'+self.name+'/'+EPISODE_CACHE_FILE_NAME):
				for line in fileinput.input(HOME_DIR+'/podcast/'+self.name+'/'+EPISODE_CACHE_FILE_NAME):
					#print "line : ", line
					if line != '\n':
						e = Episode(self.name, line)
						if not e in self.episodes:
							#add to list
							self.episodes.append(e)
				fileinput.close()
			#order episodes by date, most recent first
			self.episodes.sort(reverse=True)
		print ">>>>>>>>>>>>>>> num of episodes ", len(self.episodes)
		'''while len(self.episodes) > MAX_EPISODE_PER_CHANNEL:
			e = self.episodes.pop()
			if os.path.isfile(e.path()):
				os.remove(e.path())'''

	def update_local_cache(self):
		f = open(HOME_DIR+'/podcast/'+self.name+'/'+EPISODE_CACHE_FILE_NAME, 'wb+')
		for e in self.episodes:
			f.write(e.title)
			f.write(":-:")
			f.write(e.date.strftime("%a, %d %b %Y %H:%M:%S %z"))
			f.write(":-:")
			f.write(e.url)
			f.write("\n")
		f.close()

	def to_cmd(self):
		r = []
		r.append("channel_name:")
		r.append(self.name)
		r.append('\n')
		r.append("channel_date:")
		try:
			r.append(self.episodes[0].date.strftime("%d/%m/%Y %H:%M"))
		except:
			pass
		r.append('\n')
		return r

	def __cmp__(self, other):
		return self.name > other.name

#import urllib2

class Episode():
	def __init__(self, channel_name, data):
		self.channel_name = channel_name
		a = data.split(":-:")
		self.title = a[0].replace("\"", "").strip()
		try :
			self.date = parse(a[1])
		except:
			#usually due to bad week name
			# remove it, as it's marked by a comma ,
			ind = a[1].find(',')
			self.date = parse(a[1][ind:])
		self.url = a[2][:-1]

	def __cmp__(self, other):
		return (self.date - other.date).total_seconds()

	#deprecated
	'''def already_dl(self):
		return os.path.exists(self.path())

	def download(self):
		pass
		if not self.already_dl():
			urllib.urlretrieve(self.url, self.path())
			#urllib2.urlopen(self.url)
		#debug
		else:
			print "episode already dl"

	def path(self):
		return HOME_DIR+'/podcast/'+self.channel_name+'/'+self.date.strftime("%Y_%m_%d_%H_%M_%S.episode")'''

	def __str__(self):
		return self.date.strftime("%a, %d %b %Y %H:%M:%S %z")+" "+self.title

	def to_cmd(self):
		r = []
		r.append("episode_date:")
		r.append(self.date.strftime("%d/%m/%Y %H:%M"))
		r.append('\n')
		r.append("episode_name:")
		r.append(self.title)
		r.append('\n')
		return r

if __name__=="__main__":
	p = PodcastManager()
	#p.start()
	p.update()
	p.run()
	#time.sleep(3.0)
	#print "download test"
	#p.channels[0].episodes[0].download()
