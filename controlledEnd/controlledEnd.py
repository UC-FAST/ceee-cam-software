import abc


class ControlledEnd(abc.ABC):
    def __init__(self, _id):
        self._id = _id
        self._irq = None
        self._msgSender = None

    @abc.abstractmethod
    def centerPressAction(self):
        pass

    @abc.abstractmethod
    def upPressAction(self):
        pass

    @abc.abstractmethod
    def downPressAction(self):
        pass

    @abc.abstractmethod
    def leftPressAction(self):
        pass

    @abc.abstractmethod
    def rightPressAction(self):
        pass

    @abc.abstractmethod
    def circlePressAction(self):
        pass

    @abc.abstractmethod
    def trianglePressAction(self):
        pass

    @abc.abstractmethod
    def direction(self, direction):
        pass

    def centerReleaseAction(self):
        pass

    def upReleaseAction(self):
        pass

    def downReleaseAction(self):
        pass

    def leftReleaseAction(self):
        pass

    def rightReleaseAction(self):
        pass

    def circleReleaseAction(self):
        pass

    def triangleReleaseAction(self):
        pass

    @abc.abstractmethod
    def msgReceiver(self, sender, msg):
        pass

    def msgSender(self, func):
        self._msgSender = func

    def irq(self, func):
        self._irq = func

    @abc.abstractmethod
    def mainLoop(self):
        pass

    def onExit(self):
        pass

    def onEnter(self, lastID):
        pass

    @property
    def id(self):
        return self._id
