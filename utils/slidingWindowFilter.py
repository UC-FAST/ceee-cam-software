class SlidingWindowFilter:
    def __init__(self, maxSize):
        self.__maxSize = maxSize
        self.__list = list()
        self.__sum = 0
        self.__size = 0

    def addData(self, data):
        if self.__size == self.__maxSize:
            self.__sum -= self.__list.pop(0)
        else:
            self.__size += 1
        self.__list.append(data)
        self.__sum += data
        return self

    def calc(self):
        return self.__sum / self.__size
