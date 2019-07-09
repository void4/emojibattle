# Start with a basic flask app webpage.
import os
from random import random, choice
from string import ascii_uppercase
from time import sleep
from threading import Thread, Event
from collections import defaultdict
from pickle import loads, dumps

from trueskill import Rating, rate_1vs1, quality_1vs1

from flask_socketio import SocketIO, emit
from flask import Flask, render_template, url_for, copy_current_request_context

#from tinydb import TinyDB, Query
#db = TinyDB("db.json")

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.config['DEBUG'] = True

# Turn the flask app into a socketio app
socketio = SocketIO(app, async_mode="threading")

# Async socketio update thread
thread = Thread()
thread_stop_event = Event()

#Grabbed from
#https://unicode.org/emoji/charts-12.0/full-emoji-list.html
#with
#https://stackoverflow.com/questions/31912136/each-is-not-a-function
emojis = open("emojis.txt", encoding="utf8", errors="ignore").read()
def choose():
	return choice("ABC")
	#return choice(ascii_uppercase)
	#return choice(emojis)

class RandomThread(Thread):
	def __init__(self):
		self.delay = 10
		super(RandomThread, self).__init__()

	def pingClients(self):
		global battle
		print("Starting the async ping thread.")
		while not thread_stop_event.isSet():
			a = choose()
			b = a
			while b == a:
				b = choose()
			print(a,"vs",b)
			battle = {'a': a, 'b':b}
			sendbattle()
			sendratings()
			savedb()
			sleep(self.delay)

	def run(self):
		self.pingClients()

def sendbattle():
	socketio.emit('newnumber', battle, namespace='/test')

@app.route('/')
def index():
	#only by sending this page first will the client be connected to the socketio instance
	return render_template('index.html')


DBFILE = "db.json"
def savedb():
	global ratings
	with open(DBFILE, "wb+") as db:
		db.write(dumps(ratings))

if os.path.exists(DBFILE):
	with open(DBFILE, "rb") as db:
		ratings = loads(db.read())
else:
	ratings = defaultdict(Rating)
battle = {"a":None,"b":None}

def getranks():
	sortedratings = sorted(list(ratings.values()), key=lambda x:x.mu, reverse=True)

	ra = sortedratings.index(ratings[battle["a"]]) + 1
	rb = sortedratings.index(ratings[battle["b"]]) + 1

	return ra, rb

@socketio.on("click", namespace="/test")
def test_click(msg):

	cura = battle["a"]
	curb = battle["b"]

	olda = ratings[cura]
	oldb = ratings[curb]

	oldranka, oldrankb = getranks()

	oldamu = olda.mu
	oldbmu = oldb.mu

	if msg["data"] == 0:
		ratings[cura], ratings[curb] = rate_1vs1(olda, oldb)
	elif msg["data"] == 1:
		ratings[curb], ratings[cura] = rate_1vs1(oldb, olda)

	diffa = ratings[cura].mu-oldamu
	diffb = ratings[curb].mu-oldbmu

	newranka, newrankb = getranks()

	diffranka = oldranka-newranka
	diffrankb = oldrankb-newrankb

	sendratings()

	senddiffs(diffa, diffranka, diffb, diffrankb)

def f2s(v):
	return "%i" % round(v*40)

def addplus(v, trim=True):
	if trim:
		v = f2s(v)
	else:
		v = str(v)
	v = "+" + v if not v.startswith("-") else v
	return v

def senddiffs(da,dra,db,drb):
	da = addplus(da)
	db = addplus(db)
	dra = addplus(dra, False)
	drb = addplus(drb, False)

	socketio.emit('diffs', [da, db, dra, drb], namespace='/test', broadcast=True)

def sendratings():
	socketio.emit('newratings', [f2s(ratings[battle["a"]].mu), f2s(ratings[battle["b"]].mu), *getranks()], namespace='/test', broadcast=True)


@socketio.on('connect', namespace='/test')
def test_connect():
	# Need visibility of the global thread object
	global thread
	print('Client connected')

	if not thread.isAlive():
		print("Starting Thread")
		thread = RandomThread()
		thread.start()

	sendbattle()
	sendratings()

@socketio.on('disconnect', namespace='/test')
def test_disconnect():
	print('Client disconnected')


if __name__ == '__main__':
	socketio.run(app)
