import cv2
import numpy as np
import math

class HandGestureRecognition:
    """Hand gesture recognition class
        This class implements an algorithm for hand gesture recognition
        based on a single-channel input image showing the segmented hand region.
        The algorithm will then find the hull of the segmented hand region and
        convexity defects therein. Based on this information,an estimate on the
        number of extended fingers is derived.
    """
    
    def __init__(self):
        """Class constructor
            initializes all necessary parameters.
        """
        self.kernel = kernel = np.ones((3,3),np.uint8)

        # cut-off angle (deg): everything below this is a convexity point that
        # belongs to two extended fingers
        self.angle_cuttoff = 80.0

    def recognize(self, img):
        """Recognizes hand gesture in a single-channel grayscale image
            This method estimates the number of extended fingers based on
            an image showing a hand region.
        """
        # further segment hand region
        segment = self._segmentHand(img)
        try:
            # find the hull of the segmented area, and based on that find the
            # convexity defects
            contours, defects = self._findHullDefects(segment)
            return self._detectGesture(contours, defects, img)
        except:
            # detect the number of fingers depending on the contours and convexity
            # defects, then draw defects that belong to fingers green, others red
            segment = cv2.cvtColor(segment, cv2.COLOR_GRAY2BGR)
            return (0,segment)

    def _segmentHand(self, img):
        """This method applies further filtering to mitigate noise around masked hand
        """
        mask = cv2.erode(img, self.kernel, iterations = 2)
        mask = cv2.dilate(mask, self.kernel, iterations = 2)
        mask = cv2.GaussianBlur(mask,(5,5),0)
        return mask
        
    def _findHullDefects(self, segment):
        """Find hull defects
            This method finds all defects in the hull of a segmented arm
            region.
        """
        _,contours,hierarchy = cv2.findContours(segment,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)

        # find largest area contour
        max_contour = max(contours, key = lambda x: cv2.contourArea(x))
        epsilon = 0.01*cv2.arcLength(max_contour, True)
        max_contour = cv2.approxPolyDP(max_contour, epsilon, True)
        
        # find convexity hull and defects
        hull = cv2.convexHull(max_contour, returnPoints=False)
        defects = cv2.convexityDefects(max_contour, hull)

        return (max_contour, defects)

    def _detectGesture(self, contours, defects, img):
        """Detects the number of extended fingers, based on a contour and
            convexity defects. It will annotate an RGB color image of the
            segmented hand region with all relevant defect points and the hull.
        """
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

        # if there are no convexity defects, possibly no hull found or no
        # fingers extended
        if defects is None:
            return ['0', img]

        # assume the wrist generates two convexity defects (one on each
        # side), so if there are no additional defect points, there are no
        # fingers extended
        if len(defects) <= 2:
            return ['0', img]

        # if there is a sufficient amount of convexity defects, we will find a
        # defect point between two fingers so to get the number of fingers,
        # start counting at 1
        num_fingers = 1

        for i in range(defects.shape[0]):
            start_idx, end_idx, farthest_idx, _ = defects[i,0]
            start = tuple(contours[start_idx][0])
            end = tuple(contours[end_idx][0])
            far = tuple(contours[farthest_idx][0])

            # draw the hull
            cv2.line(img, start, end, [0, 255, 0], 2)

            # if angle is below a threshold, defect point belongs to two
            # extended fingers
            if angleRad(np.subtract(start, far),
                        np.subtract(end, far)) < deg2Rad(self.angle_cuttoff):
                num_fingers += 1

                # draw point as green
                cv2.circle(img, far, 5, [0, 255, 0], -1)
            else:
                # draw point as red
                cv2.circle(img, far, 5, [0, 0, 255], -1)

        return (min(5, num_fingers), img)

def angleRad(v1, v2):
    """Convert degrees to radians
    This method converts an angle in radians e[0,2*np.pi) into degrees
    e[0,360)
    """
    return np.arctan2(np.linalg.norm(np.cross(v1, v2)), np.dot(v1, v2))
    
def deg2Rad(angle_deg):
    """Angle in radians between two vectors
    returns the angle (in radians) between two array-like vectors
    """
    return angle_deg/180.0*np.pi
    
