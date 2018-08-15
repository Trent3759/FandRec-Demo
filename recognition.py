import sys, cv2, numpy as np, os, time, dlib, imutils
from pathlib import Path
from gesture import *
from database import DBHelper
from imutils.video import WebcamVideoStream
DBHelper = DBHelper.DBHelper


class Recognition:
    """Face recognition and hand detection class
        This class makes use of machine learning algorithms for processing RGB frames
        from a webcam. A caffe neural network model detects faces in a given frame. Upon
        detection, the face images are either used to train a face recognizer or passed
        through an existing recognizer in search of a predicted match. If a match is made,
        the algorithm will search for the recognized person's hands and send them to the
        hand recognition class for gesture classification.
    """
    # global class variables
    path_facemodel = "./models/face_classifier.caffemodel"
    path_faceproto = "./models/face_classifier.prototxt.txt"
    facenet = cv2.dnn.readNetFromCaffe(path_faceproto, path_facemodel)
    hand_classifier = cv2.CascadeClassifier("./models/aGest.xml")
    gesture_recognizer = HandGestureRecognition()
    font = cv2.FONT_HERSHEY_SIMPLEX
    sample_size = 100

    
    def __init__(self):

        # instance variables
        self.frame_dimensions = None
        self.samples = 0
        self.sample_images = []
        self.gesture_tracker = None
        self.last_gest = ""
        self.rec_trained = False
        self.black_mask = np.zeros((480,640),np.uint8)
        self.bg_model = BackgroundModel()
        
        
        # bools for altering webpage control flow
        self.is_registering = False
        self.reg_complete = False
        
        # initialize OpenCV's local binary pattern histogram recognizer
        # and load saved training data
        self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        if Path('./training_data/recognizer.yml').is_file():
            self.recognizer.read('./training_data/recognizer.yml')
            self.rec_trained = True
        

    def processFrame(self, frame, username):
        """Prepares frame for either face recognition or hand gesture detection and
            performs additional processing for display.
            :param frame:
            :param username:
            :returns: (frame, username, gesture), processed frame, a name of a recognized
                        user, and the id number of a detected hand gesture
        """
        # get frame height and width
        if self.frame_dimensions is None:
            self.frame_dimensions = frame.shape[:2]
        
        # mirror and split raw frame into color, grayscale
        frame = cv2.UMat(frame)
        frame = cv2.flip(frame, 1)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # equalizing the histogram improves results for detection algorithms
        # in varying lighting conditions
        gray = cv2.equalizeHist(gray)
        frame = cv2.UMat.get(frame)
        
        # reg_complete bool indicates whether registration has been completed
        # during this method call
        self.reg_complete = False

        gesture = '0'  # default value will not send tag
        
        if self.is_registering:
            frame = self._register(frame, gray, username)
            self._displayProgress(frame)
        elif self.rec_trained:
            frame, username, gesture = self._detect(frame, gray)
            self._displayGesture(frame)
        
        return (frame, username, gesture)
        
    
    def _register(self, frame, gray, username):
        """Detects faces in frames and uses them to train a face recognition algorithm.
            Face data is associated with the given username.
            :param frame: an 8 bit, 3-channel UMat object
            :param gray: an 8-bit, 1-channel ndarray
            :param username: name of registering user
        """ 
        if self.samples < self.sample_size:
            
            # Find all faces and store only the location of the largest (closest to the camera)
            faces = self._findFaces(frame)
            max_area = 0
            x = 0
            y = 0
            w = 0
            h = 0
            for (startX,startY,endX,endY) in faces:
                c_w = endX - startX
                c_h = endY - startY
                if c_w * c_h > max_area:
                    x = startX
                    y = startY
                    w = c_w
                    h = c_h
                    maxArea = w*h
                    
            # Resize and add face image to list for training
            if faces:
                self.samples += 1
                gray = cv2.UMat(gray,[y,y+h],[x,x+w])
                gray = cv2.resize(gray, (100, 100))
                self.sample_images.append(gray)
                    
        else:
            # Finished collecting face data
            # Associate registering user id with training data
            db = DBHelper()
            user_id = db.getIDByUsername(username)
            id_array = [user_id] * self.sample_size

            for i in range(self.sample_size):
                self.sample_images[i] = cv2.UMat.get(self.sample_images[i])

        # Update or create new face recognizer
            if Path('./training_data/recognizer.yml').is_file():
                self.recognizer.update(self.sample_images, np.array(id_array))
            else:
                self.recognizer.train(self.sample_images, np.array(id_array))
            self.recognizer.write('./training_data/recognizer.yml')
            
            # registration complete
            self.reg_complete = True
            self.rec_trained = True
            
            # reset variables before detection begins
            self._reset()
            
        return frame


    def _detect(self, frame, gray):
        """Detects faces, compares them registered faces, and detects hands for gesture
            recognition if a match is found.
            :param frame: a BGR color image for display
            :param gray: a grayscale copy of the passed BGR frame
            :returns: (out_frame, username, gesture) the processed frame
                for display on webpage, the detected user, the detected gesture
        """
        username = ""
        gesture = "0"
        num_fingers = 0
        
        if self.gesture_tracker is None: # not currently tracking hands
            faces = self._findFaces(frame)
            
            for (startX,startY,endX,endY) in faces:
                # text is displayed at y coordinate
                y = startY - 10 if startY - 10 > 10 else startY + 10
                
                # gray_face sometimes gets converted back to ndarray, throwing an error
                # I do not know why
                try:
                    gray_face = cv2.UMat(gray,[startY,endY],[startX,endX])
                except:
                    gray_face = gray[startY:endY,startX:endX]

                # optional resize for slightly improved performance 
                gray_face = cv2.resize(gray_face, (100, 100))
                user_id, confidence = self.recognizer.predict(gray_face)
                gray = cv2.UMat.get(gray)

                # mask detected face region with solid black to avoid false positives in hand detection
                gray[startY:endY,startX:endX] = self.black_mask[startY:endY,startX:endX]

                # for LBPH recognizer, lower confidence scores indicate better results
                if confidence <= 80: # user is recognized
                    db = DBHelper()
                    username = db.getUsernameById(user_id)
                    cv2.putText(frame, username,
                                (startX, y),
                                self.font, .6,
                                (225,105,65), 2)
                else:
                    # face belongs to unknown user
                    cv2.putText(frame, "unknown",
                                (startX, y),
                                self.font, .6,
                                (0, 0, 255), 2)

            # a user is recognized and hand detection begins
            if username is not "" and faces:
                hands = self.hand_classifier.detectMultiScale(gray, 1.3, 5)

                # detected hand region is resized to allow for tracking an open hand
                for (x,y,w,h) in hands:
                    x_mid = (w//2)
                    y = int(y-h*1.3)
                    x = int(x-x_mid*1.5)
                    w = int(w+3*x_mid)
                    h = int(h*2+h*0.7)
                    cv2.rectangle(frame,(x,y),(x+w,y+h),(0, 0, 255), 2)

                    # only attempt to recognize hand gesture if background model is finished calibrating
                    if self.bg_model.calibrated:
                        self.gesture_tracker = GestureTracker(frame,(x,y,w,h))

            # if no faces are in the frame, assume the frame is background
            if not self.bg_model.calibrated and not faces:
                self.bg_model.runAverage(frame)

        else: # hand has been detected and is being tracked by gesture_tracker
            timed_out, (x,y,w,h) = self.gesture_tracker.update(frame)
            if timed_out:
                self.gesture_tracker = None
            try:
                gray = cv2.UMat.get(gray)
                difference = cv2.absdiff(self.bg_model.background.astype("uint8")[y:y+h,x:x+w],
                                         gray[y:y+h,x:x+w])
                foreground = cv2.threshold(difference, 25, 255, cv2.THRESH_BINARY)[1]
                gest, frame[y:y+h,x:x+w] = self.gesture_recognizer.recognize(foreground)
                self.last_gest = str(gest)
            except:
                pass
            

        return (frame, username, gesture)
    

    def _findFaces(self, frame):
        """Forwards frame to a convolutional neural network for face detection. Draws rectangles
            around detected faces.
            :param frame: 8-bit, 3-channel ndarray
            :returns: (face_regions) a list of rectangle points designating face locations
        """
        # input image can be resized up to 300x300 for improved accuracy
        # or down to 100x100 for faster performance and worse accuracy
        blob = cv2.dnn.blobFromImage(cv2.resize(frame, (150, 150)), 1.0,
                                     (150, 150), (104.0, 177.0, 123.0))
        self.facenet.setInput(blob)
        detected_faces = self.facenet.forward()
        h,w = self.frame_dimensions
        face_regions = []

        for i in range(0, detected_faces.shape[2]):
            confidence = detected_faces[0,0,i,2]
            if confidence > .4:
                box = detected_faces[0,0,i,3:7] * np.array([w,h,w,h])
                (startX, startY, endX, endY) = box.astype("int")
                if (startX >= 0 and startY >= 0 and
                    endX <= w and endY <= h):
                    face_regions.append((startX, startY, endX, endY))
                    cv2.rectangle(frame, (startX, startY), (endX, endY),
                                  (225,105,65), 2)

        return face_regions
    

    def _displayProgress(self, frame):
        """Displays percentage of required samples attained for training the face recognizer
            :param frame: the displayed color frame
            :side effect: input frame is modified
        """
        x, y = self.frame_dimensions
        percent_complete = str(int(self.samples/self.sample_size*100)) + "%"
        cv2.putText(frame, percent_complete,
                    (25, 30), self.font, 1.2,
                    (0,255,0), 2)


    def _displayGesture(self, frame):
        """Displays last detected hand gesture ID
            :param frame: the displayed color frame
            :side effect: input frame is modified
        """
        x, y = self.frame_dimensions
        message = "Gesture:  " + self.last_gest
        cv2.putText(frame, message,(25, 30),
                    self.font, 1.2,(225,105,65), 2)


    def _reset(self):
        """reinitializes variables used in gesture detection state
        """
        self.is_registering = False
        self.samples = 0
        self.sample_images = []

class GestureTracker:
    """Hand tracking class
    """
    # seconds user has after hand tracking begins to form hand gesture
    gesture_timeout = 4
    
    def __init__(self, frame, rect):
        self.timed_out = False
        self.start_time = time.time()
        self.corr_tracker = dlib.correlation_tracker()
        x,y,w,h = rect
        self.corr_tracker.start_track(frame, dlib.rectangle(x,y,
                                                            x+w,
                                                            y+h))

    def update(self, frame):
        
        tracking_quality = self.corr_tracker.update(frame)
        
        if (time.time() - self.start_time) >= self.gesture_timeout:
            self.timed_out = True
        
        tracked_position = self.corr_tracker.get_position()
        x = int(tracked_position.left())
        y = int(tracked_position.top())
        w = int(tracked_position.width())
        h = int(tracked_position.height())
        cv2.rectangle(frame, (x, y),
                      (x + w, y + h),
                      (0,255,0), 2)
            
        return (self.timed_out, (x,y,w,h))


class BackgroundModel:
    """Frame background model class
        This class uses openCV image processing algorithms to generate an average
        value model from the backgrounds of a series of 30 frames. It assumes that
        the camera sending frames will remain stationary, as it does no modification
        to the model after calibration is complete
    """
    def __init__(self):
        
        self.calibrated = False
        self.background = None
        self.num_frames = 0

    def runAverage(self, frame):
        """Calculates weighted average of background pixel values in given frames.
            :param frame: 3-channel color image
            :side effect: background attribute is updated with information from new frames
            :side effect: calibrated attribute is switched to true after processing 30 frames
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)
        gray = cv2.GaussianBlur(gray, (9, 9), 0)
        if self.num_frames < 30:
            if self.background is None:
                self.background = gray.copy().astype("float")
            cv2.accumulateWeighted(gray, self.background, 0.5)
            self.num_frames += 1
        else:
            self.calibrated = True


if __name__ == "__main__":
    
    rec = Recognition()
    db = DBHelper()
    cam = WebcamVideoStream(src=0).start()
    user = ""
    
    response = input("Register new user? y or n \n")
    if response == 'y':
        rec.is_registering = True
        user = input("Enter a username: ")
        db.createUser([user, "", "", "", "", ""])
    else:
        rec.is_registering = False
    while (True):
        frame = cam.read()
        frame = cv2.resize(frame,(640,480))
        out, user, gest = rec.processFrame(frame, user)
        cv2.imshow("out", out)
        cv2.waitKey(1)
    cam.release()
    cv2.destroyAllWindows()