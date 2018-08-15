import sys

from twisted.internet import reactor
from twisted.python import log
from twisted.web.server import Site
from twisted.web.static import File

from autobahn.twisted.websocket import WebSocketServerFactory, \
	WebSocketServerProtocol, \
	listenWS

	#'lab-cam,,fan_on'

import ujson

address = u"ws://127.0.0.1:9000"

class BroadcastServerProtocol(WebSocketServerProtocol):

	def onConnect(self, request):
		print("____Sign in to CoMPES____")
		print(request.headers['user-id'])
		print(request.headers['net-id'])
		print(request.headers['hub-id'])
		print(request.headers['acu-id'])
		print(request.headers['access-key'])
		print("______END Sign In_______")

	def onOpen(self):
		self.factory.register(self)
		SRO = {'lab-speaker': {'ID': 'lab-speaker','States': ['']}, 'lab-cam': {'ID': 'lab-cam', 'States': ['fan_on', 'fan_off', 'light_on', 'light_off'] }, 'lab-mic': {}, 'lab-mod': {}, 'lab-button': {} }
		self.factory.post(ujson.dumps(SRO))

	def onMessage(self, payload, isBinary):
		print(payload.decode('UTF8'))

	def onClose(self, wasClean, code, reason):
		reason.value = "Client closed connection"
		WebSocketServerProtocol.connectionLost(self, reason)
		self.factory.unregister(self)
		print("Connection to client closed!")



class BroadcastServerFactory(WebSocketServerFactory):
	"""
	Simple broadcast server broadcasting any message it receives to all
	currently connected clients.
	"""
	protocol = BroadcastServerProtocol
	def __init__(self, url):
		WebSocketServerFactory.__init__(self, url)
		self.client = None

	def register(self, client):
		self.client = client

	def unregister(self, client):
		self.client = None

	def post(self, msg):
		print("message from HUB: " + msg)
		self.client.sendMessage(msg.encode("UTF8"))

if __name__ == '__main__':
	log.startLogging(sys.stdout)
	ServerFactory = BroadcastServerFactory(address)
	listenWS(ServerFactory)
	reactor.run()
