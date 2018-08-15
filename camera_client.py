"""
Project: FandRec
Programmed by: Trenton Sauer, Trenton Scott, David Williams
Last Modified:
Description: Client for the camera
Notes:
    1. camera_client needs to be installed and run on the machine
       that will be sending the frames to the server
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
import sys, ujson, cv2, imutils
import numpy as np

from twisted.python import log

from twisted.protocols.basic import NetstringReceiver

from autobahn.twisted.websocket import WebSocketClientFactory, \
    WebSocketClientProtocol, connectWS
from twisted.internet import reactor
from imutils.video import WebcamVideoStream
#=======================Application Interface===========================
class CameraClientProtocol(WebSocketClientProtocol):
    """
    Description: Handles the receiving messages from the
		 server and sends the frames back.
    """
    #raw_frame = cv2.UMat(np.empty((540, 1172, 3), np.uint8))

    def __init__(self):
        self.fps = 10

    def onOpen(self):
        self.sendFrames()

    def sendFrames(self):
        """
        Description: Gets a frame from the camera then
        encodes it as a json then sends it.
        """
	# Grab frame
        frame = cv2.UMat(self.factory.camera.read())
        frame = cv2.resize(frame, (640,480))

	# Compress and Package frame
        out = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])[1].tolist()
        out = ujson.dumps(out)

	# Send frame
        self.sendMessage(out.encode("utf8"))
        reactor.callLater(1/self.fps, self.sendFrames)


class CameraClientFactory(WebSocketClientFactory):
    """
    Description: Starts the video capture from the local kinect or camera.
    """
    def __init__(self, addr, cam_port):
        WebSocketClientFactory.__init__(self, addr, headers={'camera_id': 'camera1'})
        print("Starting Camera")
        self.camera = WebcamVideoStream(src=0).start()

#=================Client Main===================================

def main():
    """
    Description: Starts CameraClientProtocol defined above which sends
    the frames from the camera to the server
    """
    #STEP 1: Setup the factory
    log.startLogging(sys.stdout)
    ip_address = "127.0.0.1"
    port_num = 8091

    factory = CameraClientFactory("ws://" + ip_address + ":" + str(port_num), 0)
    factory.protocol = CameraClientProtocol
    reactor.connectTCP(ip_address, port_num, factory)

    #STEP 2: Start the reactor
    reactor.run()

if __name__ == '__main__':
    main()
