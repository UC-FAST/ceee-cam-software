import cv2

class VideoPlayer:
    def __init__(self,path,width,height):
        self.__videoReader=cv2.VideoCapture(path)
        self.__width,self.__height=width,height

    def getFirstFrame(self):
        pass
