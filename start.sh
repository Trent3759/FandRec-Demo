cd ~/Downloads/FandRec/
python3 application.py & python3 hub.py & python3 camera_client.py & sleep 2; open http://localhost:8090 & read; pkill -f camera_client.py & pkill -f hub.py & pkill -f application.py;

