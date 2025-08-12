import abc


class ControlledEnd(abc.ABC):
    def __init__(self, _id):
        self._id = _id
        self._irq = None
        self._msgSender = None

    """---Multi Direction Button Start---"""

    @abc.abstractmethod
    def centerPressAction(self):
        pass

    def centerReleaseAction(self):
        pass

    @abc.abstractmethod
    def upPressAction(self):
        pass

    def upReleaseAction(self):
        pass

    @abc.abstractmethod
    def downPressAction(self):
        pass

    def downReleaseAction(self):
        pass

    @abc.abstractmethod
    def leftPressAction(self):
        pass

    def leftReleaseAction(self):
        pass

    @abc.abstractmethod
    def rightPressAction(self):
        pass

    def rightReleaseAction(self):
        pass

    """---Multi Direction Button End---"""

    """---Multi Function Button Start---"""

    @abc.abstractmethod
    def circlePressAction(self):
        pass

    @abc.abstractmethod
    def squarePressAction(self):
        pass

    @abc.abstractmethod
    def crossPressAction(self):
        pass

    @abc.abstractmethod
    def shutterPressAction(self):
        pass

    """---Multi Function Button End---"""

    """---Rotary Encoder Start---"""

    @abc.abstractmethod
    def rotaryEncoderClockwise(self):
        pass

    @abc.abstractmethod
    def rotaryEncoderCounterClockwise(self):
        pass

    @abc.abstractmethod
    def rotaryEncoderSelect(self):
        pass

    """---Rotary Encoder End---"""

    """---Communication Function Start---"""
    @abc.abstractmethod
    def msgReceiver(self, sender, msg):
        pass

    def msgSender(self, func):
        self._msgSender = func

    """---Communication Function End---"""

    def irq(self, func):
        self._irq = func

    @abc.abstractmethod
    def mainLoop(self):
        pass

    def onExit(self):
        pass

    def onEnter(self, lastID):
        pass

    def active(self):
        pass

    def inactive(self):
        pass

    @property
    def id(self):
        return self._id
