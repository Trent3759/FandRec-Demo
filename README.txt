Project FandRec

Requirements for server:
  Python v3.5 or higher
   pip install these:
    numpy wsaccel ujson autobahn twisted opencv-contrib-python flask

Requirements for camera client:
  Python v3.5 or higher
   pip install these:
    numpy wsaccel ujson autobahn twisted opencv-contrib
	OpenCV must be built with Openni2 support in order to read depth 
	frames from a compatible sensor

1. start the server using:
    python application.py

2. start the client using:
    python camera_client.py

3. connect to the webpage using:
    127.0.0.1:8090
