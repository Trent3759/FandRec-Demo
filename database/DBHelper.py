"""
	Created by Trenton Scott
	Created on 02/23/2018
	Purpose: The purpose of this class is to assist with database interaction 
	on the FandRec client. 
"""

import sqlite3, random, hashlib

class DBHelper:
	global conn
	global curr 
	global keepConnOpen
	
	def __init__(self, active = False):
		"""
			
			Created by Trenton D Scott
			Output: N/A
			Description: Initializes DBHelper
			Usage: DBHelper(active)
				active	--	if True the database connection will stay open until
							closed. If false, the database connection will close 
							after 1 transaction. 
		
		"""
		
		self.db_connect()
		try:
			conn.execute("SELECT * FROM Users")
		except:
			#if the above throws an error, the table does not exist and will be created. 
			#this should only occurs during initial setup. 
			conn.execute("CREATE TABLE Users ( ID INTEGER PRIMARY KEY, Username varchar(20) UNIQUE, Password varchar(20),"
			"Salt varchar(16), HUB_ID varchar(50), NET_ID varchar(50), ACU_ID varchar(20), ACCESS_KEY varchar(20))")
			try:
				conn.execute("SELECT * FROM Gestures")
			except:
				#if the above throws an exception, here we will assume the table is corrupt or
				#not available. 
				conn.execute("CREATE TABLE Gestures (Username varchar(20), Gesture varchar(10), Function varchar(25))")
				
		global keepConnOpen
		keepConnOpen = active;
		
		
	def db_connect(self):
		"""
			
			Created by Trenton D Scott
			Output: N/A
			Description: Connected to database
			Usage: This function should only be called by 
		"""
		#connect to the database. 
		try:
			global conn
			conn = sqlite3.connect('database/database.db')
		except:
			print("An error was encountered while trying to connect to the database. ")
		global curr
		curr = conn.cursor()	

	def createUser(self, credentials):
		"""
			
			Created by Trenton D Scott
			Output: Boolean
			Description: Stores new user in the database. 
			Usage: DBHelper.createUser([username, password, hub-id, net-id])
		
		"""
		CHARS = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
		salt= ""
		for i in range(16):
			salt += random.choice(CHARS)
		
		encodedPass = (credentials[1] + salt).encode()
		sec_pass = hashlib.sha256(encodedPass)
		
		HUB_ID = credentials[2]
		NET_ID = credentials[3]
		ACU_ID = credentials[4]
		ACCESS_KEY = credentials[5]


		try:
			conn.execute("INSERT INTO Users (Username, Password, Salt, HUB_ID, NET_ID, ACU_ID, ACCESS_KEY) VALUES (?,?,?,?,?,?,?)", (credentials[0], str(sec_pass.hexdigest()), salt, HUB_ID, NET_ID, ACU_ID, ACCESS_KEY))
			conn.commit()
			return True
		except sqlite3.IntegrityError:
			return False

		if not keepConnOpen: self.disconnect()

	def authenticate(self, credentials):
		"""
			
			Created by Trenton D Scott
			Output: Boolean
			Description: Returns true on successful authentication 
			Usage: DBHelper.getUsernames()
		
		"""
		username = credentials[0]
		password = credentials[1]

		
		try: 
			try:
				curr.execute("SELECT Salt FROM Users WHERE Username=?", (username,))
				salt = curr.fetchone()[0]
				encodedPass = (password + salt).encode()
				testHash = hashlib.sha256(encodedPass).hexdigest()

				curr.execute("SELECT Password FROM Users WHERE Username=?", (username,))

				storedHash = curr.fetchone()[0]
			except:
				return False

			if (testHash == storedHash):
				return True
			else:
				return False

		except:
			print("Could not execute query on database. The database could be closed. ")
		if not keepConnOpen: self.disconnect()

		
		
	def getUsernames(self):
		"""
			
			Created by Trenton D Scott
			Output: List [String, ...]
			Description: Returns username from database based on ID. 
			Usage: DBHelper.getUsernames()
		
		"""
		curr.execute("SELECT Username from Users");
		userList = []
		usernames = curr.fetchall()
		if not keepConnOpen: self.disconnect()
		for x in usernames:
			userList.append(x[0])
		return userList

	def getUsernameById(self, ID):
		"""
			
			Created by Trenton D Scott
			Output: String
			Description: Returns username from database based on ID. 
			Usage: DBHelper.getUserNameById(Integer)
		
		"""
		curr.execute("SELECT Username FROM Users WHERE ID=?", (ID,))
		try:
			return curr.fetchone()[0]
		except: 
			return "NoUserExists"
		if not keepConnOpen: self.disconnect()
		
	def getIDByUsername(self, username):
		"""
			
			Created by Trenton D Scott
			Output: String
			Description: Returns ID from database based on username. 
			Usage: DBHelper.getIdByUsername(String)
		
		"""
		curr.execute("SELECT ID FROM Users WHERE Username=?", (username,))
		try: 
			return curr.fetchone()[0]
		except:
			return "NoUserExists"
		if not keepConnOpen: self.disconnect()
		
	def getHubIdByUsername(self, username):
		"""
		
			Created by Trenton D Scott
			Output: String
			Description: Returns Hub ID from database based on username.  
			Usage: DBHelper.getHubIdByUsername(Integer)
		
		"""
		curr.execute("SELECT HUB_ID FROM Users WHERE Username=?", (username,))
		try: 
			return curr.fetchone()[0]
		except:
			return "NoUserExists"
		if not keepConnOpen: self.disconnect()
		
	def getNetIdByUsername(self, username):
		"""
		
			Created by Trenton D Scott
			Output: String
			Description: Returns Net ID from database based on username. 
			Usage: DBHelper.getUserNameById(Integer)
		
		"""
		curr.execute("SELECT NET_ID FROM Users WHERE Username=?", (username,))
		try: 
			return curr.fetchone()[0]
		except:
			return "NoUserExists"
		if not keepConnOpen: self.disconnect()
		
	def getACUByUsername(self, username):
		"""
		
			Created by Trenton D Scott
			Output: String
			Description: Returns ACU ID from database based on username. 
			Usage: DBHelper.getUserNameById(Integer)
		
		"""
		curr.execute("SELECT ACU_ID FROM Users WHERE Username=?", (username,))
		try: 
			return curr.fetchone()[0]
		except:
			return "NoUserExists"
		if not keepConnOpen: self.disconnect()
		
	def getAccessKeyByUsername(self,username):
		"""
		
			Created by Trenton D Scott
			Output: String
			Description: Returns access key from database based on username. 
			Usage: DBHelper.getUserNameById(Integer)
		
		"""
		curr.execute("SELECT ACCESS_KEY FROM Users WHERE Username=?", (username,))
		try: 
			return curr.fetchone()[0]
		except:
			return "NoUserExists"
		if not keepConnOpen: self.disconnect()
		
		
	#***************************Gesture Information********************************
	def addGesture(self, username, gesture, function):
		"""
		
			Created by Trenton D Scott
			Output: Boolean
			Description: Returns list of gestures  
			Usage: DBHelper.addGesture(String username, String gesture_name, String function)
			
		"""
		
		try:
			conn.execute("DELETE FROM Gestures WHERE Username=? AND Gesture=?", (username, gesture,))
			#above line removes the gesture if it current exists 
			conn.execute("INSERT INTO Gestures (Username, Gesture, Function) VALUES (?,?,?)", (username, gesture, function))
			conn.commit()
			return True
		except:
			return False
		
	def getGesturesByUsername(self, username):
		"""
		
			Created by Trenton D Scott
			Output: List [Tuple, ...]
			Description: Returns list of gestures  
			Usage: DBHelper.getGesturesByUsername(String)
			
		"""
		try: 
			curr.execute("SELECT Gesture, Function FROM Gestures WHERE Username=?", (username, ));
			gestures = curr.fetchall()
			if not keepConnOpen: self.disconnect()
			return gestures
		except:
			return None
			
	def getGestureFunction(self, username, gesture):
		"""
		
			Created by Trenton D Scott
			Output: String
			Description: Returns gesture function based on username and gesture. 
			Usage: DBHelper.getGesture(String username, Integer gesture)
			
		"""
		try: 
			curr.execute("SELECT Function FROM Gestures WHERE Username=? AND Gesture=?", (username, gesture, ));
			gesture = curr.fetchone()[0]
			if not keepConnOpen: self.disconnect()
			return gesture
		except:
			return None
			
	def dump_table(self):
		"""
			
			Created by Trenton D Scott
			Output: List [String, ...]
			Description: Returns username from database based on ID. 
			Usage: DBHelper.getUsernames()
		
		"""
		curr.execute("SELECT * from Gestures")
		data = curr.fetchall()
		print(data)
		
	def disconnect(self):
		conn.close()
