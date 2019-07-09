# Start with a basic flask app webpage.
from flask_socketio import SocketIO, emit
from flask import Flask, render_template, url_for, copy_current_request_context
from random import random, choice
from string import ascii_uppercase
from time import sleep
from threading import Thread, Event

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.config['DEBUG'] = True

#turn the flask app into a socketio app
socketio = SocketIO(app, async_mode="threading")

#random number Generator Thread
thread = Thread()
thread_stop_event = Event()

#Grabbed from
#https://unicode.org/emoji/charts-12.0/full-emoji-list.html
#with
#https://stackoverflow.com/questions/31912136/each-is-not-a-function
emojis = open("emojis.txt", encoding="utf8", errors="ignore").read()
def choose():
	#return choice(ascii_uppercase)
	return choice(emojis)

class RandomThread(Thread):
	def __init__(self):
		self.delay = 10
		super(RandomThread, self).__init__()

	def randomNumberGenerator(self):
		global battle
		print("Making random numbers")
		while not thread_stop_event.isSet():
			a = choose()
			b = a
			while b == a:
				b = choose()
			print(a,"vs",b)
			battle = {'a': a, 'b':b}
			sendbattle()
			sendratings()
			sleep(self.delay)

	def run(self):
		self.randomNumberGenerator()

def sendbattle():
	socketio.emit('newnumber', battle, namespace='/test')

@app.route('/')
def index():
	#only by sending this page first will the client be connected to the socketio instance
	return render_template('index.html')

from trueskill import Rating, rate_1vs1, quality_1vs1
from collections import defaultdict

ratings = defaultdict(Rating)
battle = {"a":None,"b":None}

@socketio.on("click", namespace="/test")
def test_click(msg):
	print(msg)

	olda = ratings[battle["a"]]
	oldb = ratings[battle["b"]]

	oldamu = olda.mu
	oldbmu = oldb.mu

	if msg["data"] == 0:
		ratings[battle["a"]], ratings[battle["b"]] = rate_1vs1(olda, oldb)
	elif msg["data"] == 1:
		ratings[battle["b"]], ratings[battle["a"]] = rate_1vs1(oldb, olda)

	print(oldamu, olda.mu, type(oldamu))
	diffa = ratings[battle["a"]].mu-oldamu
	diffb = ratings[battle["b"]].mu-oldbmu

	sendratings()

	senddiffs(diffa, diffb)

def addplus(v):
	print(v)
	v = str(v)
	v = "+" + v if not v.startswith("-") else v
	return v

def senddiffs(da,db):
	da = addplus(da)
	db = addplus(db)

	socketio.emit('diffs', [da, db], namespace='/test', broadcast=True)

def sendratings():
	socketio.emit('newratings', [ratings[battle["a"]].mu, ratings[battle["b"]].mu], namespace='/test', broadcast=True)


@socketio.on('connect', namespace='/test')
def test_connect():
	# need visibility of the global thread object
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
