"""
Project: Project FandRec
Last Modified: 11/21/2017
Description: Takes in a frame and finds faces in the picture. If the frame contains a face that has been registered,
                         it will also check next to the face for fingers held up. If the number of fingers is mapped to action to be
                         taken then a tag will be sent to CoMPES to tell it what to do.
Notes:
        1. The camera client must be running on the camera for it to connect to this server, the server must be running first.



Liscense:
Copyright (c) 2018, FandRec Dev Team
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
        * Redistributions of source code must retain the above copyright
          notice, this list of conditions and the following disclaimer.
        * Redistributions in binary form must reproduce the above copyright
          notice, this list of conditions and the following disclaimer in the
          documentation and/or other materials provided with the distribution.
        * Neither the name of the FandRec Dev Team nor the
          names of its contributors may be used to endorse or promote products
          derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL FandRec Dev Team BE LIABLE FOR ANY
DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
#==============================Imports=======================================
import sys, ujson, cv2, numpy as np, base64

from twisted.python import log
from twisted.internet import reactor
from twisted.web.server import Site
from twisted.web.wsgi import WSGIResource

from autobahn.twisted.websocket import WebSocketClientFactory, \
         WebSocketServerFactory, WebSocketClientProtocol, \
         WebSocketServerProtocol, connectWS, listenWS
from recognition import *

from flask import Flask, render_template, request as flask_request, make_response

app = Flask(__name__)

#~~~~~~~~~~~~ Database Import ~~~~~~~~~~~~#

from database import DBHelper
DBHelper = DBHelper.DBHelper

#==========================Global Variables==================================

ip_address = "0.0.0.0"
port_nums = [8090, 8091, 8073]
compes_ip = "192.168.86.85"
compes_ip = "ws://localhost:9000" #reassigning for using the test hub. 

app = Flask(__name__)

        
#==========================Web Server========================================

class WebComms():
        def __init__(self, url):
                #STEP-1: Start up the camera listener
                self.cam_factory = CameraFactory(url + str(port_nums[1]), self)
                
                #STEP-2: Start up webpage
                self.web_factory = WebFactory(url + "8092", self)
                
                listenWS(self.web_factory)
                listenWS(self.cam_factory)
                
                self.compes_factory = None
                
                self.user = None
                self.camera = None
                self.SRO = None
                
                
        def registerUser(self, username, password, net_id, hub_id, acu_id, access_key, camera_name = 'camera1'):
                #add camera name variable
                #send to CoMPES
                self.compes_factory = HubClientFactory("ws://127.0.0.1:9000", self, head={'user-id': username, 'pass': password, 'net-id': net_id, 'hub-id': hub_id,'acu-id': acu_id ,'access-key' : access_key})
                connectWS(self.compes_factory)
                self.user = username
                self.camera = camera_name
                return self.SRO
                
        def getSRO(self):
                if self.SRO is not None:
                        return self.SRO #gets only the states (or functions)
                else:
                        print("No SRO!")
                        
        def sendTag(self, tag):
                self.compes_factory.post(tag)


class WebsiteServerProtocol(WebSocketServerProtocol):
        """
        Programmed by: David Williams and Jake Thomas
        Description: Handles the connections from clients that are requesting to connect the server.
        """
        def __init__(self):
                WebSocketServerProtocol.__init__(self)
                self.connected = False

        def onConnect(self, request):
                """
                Programmed by: David Williams
                Description: Prints the web socket request
                """
                self.cameraName = self.factory.bridge.camera
                self.connected = True
                
                self.factory.connect("client1", self)

                print("WebSocket connection request: {}".format(request.peer))

        def onOpen(self):
                print("Connection to client opened!")

        def onMessage(self, data, isBinary):
                data = ujson.loads(data.decode("UTF8"))
                #self..clientName = data.decode("UTF8")
                self.factory.connect(self.clientName, self)


        def onClose(self, wasClean, code, reason):
                self.connected = False
                self.factory.disconnect("client1")
                print("Connection to client was closed!")

class WebFactory(WebSocketServerFactory):
        protocol = WebsiteServerProtocol
        def __init__(self, url, bridge):
                WebSocketServerFactory.__init__(self, url)
                self.frame = None
                self.connections = {}
                self.bridge = bridge

        def connect(self, clientName, connection):
                #if (clientName not in self.connections):
                self.connections[clientName] = connection
                
        def disconnect(self, clientName):
                if ("client1" in self.connections):
                        del self.connections["client1"]
                else:
                        print("Nothing to delete matching client name. ")

        def post(self, clientName, message):
                try: 
                        self.connections["client1"].sendMessage(message)
                except:
                        pass
                

#==========================Camera Server=====================================
class CameraServerProtocol(WebSocketServerProtocol):
        """
        Programmed by: David Williams
        Description: Takes in the frames from the camera client, decompresses it and stores it in the queue.
        """

        def onConnect(self, request):
                """
                Description: Prints the connection that was made with the client
                """
                self.clientName = request.headers['camera_id']
                self.factory.connect(self.clientName, self)
                print("WebSocket connection request: {}".format(request.peer))

        def onOpen(self):
                """
                Description: Prints the connection that was made with the client
                """
                print("Connection to camera_client opened.")

        def onMessage(self, data, isBinary):
                """
                Description: Decodes the image sent from the camera 
                """
                #STEP 1: Load in, convert, and decompress frame for use
                frame = ujson.loads(data.decode("utf8"))
                frame = np.asarray(frame, np.uint8)
                frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
                #post users client name here. 
                
                #frame = message
                
                if (self.factory.bridge.user is not None):
                        frame, username, gesture = self.factory.rec.processFrame(frame, self.factory.bridge.user)
                        if (gesture != '0'): #gesture is '0' by default
                                db = DBHelper(True)
                                gest_func = db.getGestureFunction(username, "gest_" + str(gesture))

                                acu = db.getACUByUsername(username)
                                tag = acu + ",," + str(gest_func)
                                if gest_func != None:
                                        self.factory.bridge.sendTag(tag)
                        
                if (self.factory.rec.is_registering == False and self.factory.rec.reg_complete == True):
                        self.factory.bridge.web_factory.connections["client1"].sendMessage("registration".encode("UTF8"))
                frame = cv2.UMat(frame)
                frame = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 20])[1]
                frame = base64.b64encode(frame)
                
                #send to web factory
                self.factory.bridge.web_factory.post(self.factory.bridge.user, frame)

        def onClose(self, wasClean, code, reason):
                self.factory.disconnect(self.clientName)
                print("Connection to client was closed!")


class CameraFactory(WebSocketServerFactory):
        protocol = CameraServerProtocol
        def __init__(self, url, bridge):
                WebSocketServerFactory.__init__(self, url)
                self.frame = None
                self.connections = {}
                self.bridge = bridge
                self.rec = Recognition()

        def connect(self, clientName, connection):
                if (clientName not in self.connections):
                        self.connections[clientName] = connection
                else:
                        print("Failed to register connection. ")

        def disconnect(self, clientName):
                if (clientName in self.connections):
                        del self.connections[clientName]
                else:
                        print("Nothing to delete matching client name. ")

        def post(self, clientName, message):
                self.connections[clientName].sendMessage(message.encode("UTF8"))



#==========================CoMPES Client=====================================

class HubClientProtocol(WebSocketClientProtocol):
        """
        Description: Handles the connections to the CoMPES hubs
        """
        def onConnect(self, request):
                """
                Description: Prints the connection that was made with the client
                """
                self.factory.connect("hub1", self)

        def onMessage(self, payload, isBinary):
                """
                Description: Gets the CVO from CoMPES and starts the processing of it into usable objects
                """
                self.factory.bridge.SRO = payload.decode("UTF8")
                

        def onClose(self, wasClean, code, reason):
                print("Connection to CoMPES closed")
                
class HubClientFactory(WebSocketClientFactory):
        protocol = HubClientProtocol
        def __init__(self, url, bridge, head):
                WebSocketClientFactory.__init__(self, url, headers = head)
                self.connections = {}
                self.bridge = bridge

        def connect(self, clientName, connection):
                if (clientName not in self.connections):
                        self.connections["hub1"] = connection
                else:
                        print("Failed to register connection. ")

        def disconnect(self, clientName):
                if ("hub1" in self.connections):
                        del self.connections[clientName]
                else:
                        print("Nothing to delete matching client name. ")

        def post(self, message):
                self.connections["hub1"].sendMessage(message.encode("UTF8"))
                        
#=======================================================================================
        
@app.route("/", methods = ["GET"])
def index():
        return render_template("index.html")
        
@app.route("/reg_complete", methods = ["GET"])
def reg_complete():
        resp = make_response(render_template('active.html', user=comms.user))
        return resp

@app.route("/connect", methods = ["POST"])
def connect():
        #process users credentials here. 
        
        db = DBHelper(True) #close the connection in this function. 

        username = flask_request.form['username_field']
        password = flask_request.form['password_field']
        db.dump_table()

        authSuccess = db.authenticate([username, password])

        if (authSuccess):
                #make the connection to compess here. 
                
                hub_id = db.getHubIdByUsername(username)
                net_id = db.getNetIdByUsername(username)
                acu_id = db.getACUByUsername(username)
                access_key = db.getAccessKeyByUsername(username)
                
                comms.registerUser(username, password, net_id, hub_id, acu_id, access_key)
                #comms.web_factory.rec.is_registering = True
                
                resp = make_response(render_template('active.html', user = username))
                return resp
        else:
                return render_template('index.html', message="Failed to authenticate. Please try again. ")
                
        db.disconnect()
        
@app.route("/associations", methods = ['GET','POST'])
def associations():
        if flask_request.method == 'POST':
                try:
                        #register the associations here.
                        gestureDict = {}
                        gestureDict['gest_1'] = flask_request.form['gest_1']
                        gestureDict['gest_2'] = flask_request.form['gest_2']
                        gestureDict['gest_3'] = flask_request.form['gest_3']
                        gestureDict['gest_4'] = flask_request.form['gest_4']
                        gestureDict['gest_5'] = flask_request.form['gest_5']
                        
                        db = DBHelper(True) #open in passive mode
                        for key in gestureDict:
                                db.addGesture(comms.user, key, gestureDict[key])
                        db.disconnect()
                        return render_template('active.html')
                except:
                        return "Error processing form. "
                        
        else:
                SRO = comms.getSRO()
                print("Server Message: " + SRO)
                states = ujson.loads(SRO)['lab-cam']['States']
                states_str = ','.join(states)
                print("Server Message: " + states_str)
                db = DBHelper(True)
                current_states = []
                for x in range(1,6):
                        gest = db.getGestureFunction(comms.user, 'gest_' + str(x))
                        current_states.append(gest) if gest != None else current_states.append('')
                current_states = ','.join(current_states)

                resp = make_response(render_template('associations.html', default = states_str, data = current_states))
                return resp
        
@app.route("/register", methods = ["POST", "GET"])
def register():
        if flask_request.method == 'POST': 
                username = flask_request.form['username_field']
                password = flask_request.form['password_field']
                netID = flask_request.form['network_id_field']
                hubID = flask_request.form['hub_id_field']
                acu_id = flask_request.form['acu_id_field']
                access_key = flask_request.form['access_key_field']
                
                #send username and password information to CoMPES
                
                db = DBHelper()
                dbSuccess = db.createUser([username, password, hubID, netID, acu_id, access_key])
                
                if (dbSuccess):
                        #sign in to CoMPES
                        #process items from CoMPES
                        #register face
                        
                        global comms
                        comms.registerUser(username, password, netID, hubID, acu_id, access_key)
                        comms.cam_factory.rec.is_registering = True
                        resp = make_response(render_template('profile.html', user = username))
                        return resp
                else: 
                        #display message on webpage and have the user try again. 
                        return "failed register"
        else:
                return render_template("register.html")

#==========================Main========================================
def main():
        """
        Description: Starts all of the factories and protocols needed to start the server and all of its functions.
        Notes:
                1.
                2.
        """
        log.startLogging(sys.stdout)
        #initRecognizer()
        global comms
        comms = WebComms("ws://0.0.0.0:")
        wsResourse = WSGIResource(reactor, reactor.getThreadPool(), app)

        
        #STEP-5: Setup the reactor
        reactor.listenTCP(port_nums[0], Site(wsResourse))

        #STEP-6: run
        reactor.run()

if(__name__ == "__main__"):
        main()