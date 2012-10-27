import threading, time, subprocess
from subprocess import Popen, PIPE
from threading import Thread
from Queue import Queue, Empty

#ping echo timeout in sec
ECHO_TIMEOUT = 2.0#1.5

class Watchdog(threading.Thread):
	def __init__(self):
		threading.Thread.__init__(self)
		self.shouldRun = True;

	''' To be run in separate thread
	read data from pipe and write it to queue
	this allows to read pipe data through queue without blocking'''
	def read_pipe(self, q, p):
		while self.shouldRun:
			q.put(p.stdout.readline())

	def run(self):
		#p = Popen(["ping", "-A", "192.168.1.69"], stdout=PIPE)
		p = Popen(["ping", "-i 0.5", "192.168.1.69"], stdout=PIPE)
		q = Queue()
		worker = Thread(target=Watchdog.read_pipe, args=(self, q, p))
		worker.start()
		echo_timestamp = time.time()
		while self.shouldRun:
			if time.time() - echo_timestamp > ECHO_TIMEOUT:
				#no echo for too long, close the connection
				#time.sleep(30)
				print "no echo from front end for too long ", time.time() - echo_timestamp
				self.shouldRun = False
				break;
			try:
				line = q.get_nowait()
			except:
				time.sleep(0.01)
				continue
			if line.find("Unreachable") == -1 :
				echo_timestamp = time.time()

	def stop(self):
		self.shouldRun = False

