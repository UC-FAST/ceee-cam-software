import abc
from pydoc import doc


class ControlledEnd(abc.ABC):
    """
    Abstract base class representing a controlled end device with multiple input actions and communication capabilities.

    This class defines the interface for handling various button presses, rotary encoder actions, and communication functions.
    Subclasses must implement the abstract methods to provide specific behavior for each action.

    Args:
        _id: Unique identifier for the controlled end instance.

    Attributes:
        _id (Any): The unique identifier for the instance.
        _irq (callable or None): Interrupt request handler.
        _msgSender (callable or None): Message sender function.

    Methods:
        centerPressAction(): Handle center button press (abstract).
        centerReleaseAction(): Handle center button release.
        upPressAction(): Handle up button press (abstract).
        upReleaseAction(): Handle up button release.
        downPressAction(): Handle down button press (abstract).
        downReleaseAction(): Handle down button release.
        leftPressAction(): Handle left button press (abstract).
        leftReleaseAction(): Handle left button release.
        rightPressAction(): Handle right button press (abstract).
        rightReleaseAction(): Handle right button release.
        circlePressAction(): Handle circle button press (abstract).
        squarePressAction(): Handle square button press (abstract).
        crossPressAction(): Handle cross button press (abstract).
        shutterPressAction(): Handle shutter button press (abstract).
        rotaryEncoderClockwise(): Handle rotary encoder clockwise rotation (abstract).
        rotaryEncoderCounterClockwise(): Handle rotary encoder counter-clockwise rotation (abstract).
        rotaryEncoderSelect(): Handle rotary encoder select action (abstract).
        msgReceiver(sender, msg): Handle incoming messages (abstract).
        msgSender(func): Set the message sender function.
        irq(func): Set the interrupt request handler.
        mainLoop(): Main execution loop (abstract).
        onExit(): Actions to perform on exit.
        onEnter(lastID): Actions to perform on enter.
        active(): Actions to perform when activated.
        inactive(): Actions to perform when deactivated.
        id: Property to get the unique identifier.
    """

    def __init__(self, _id):
        self._id = _id
        self._irq = None
        self._msgSender = None

    """---Multi Direction Button Start---"""

    def centerPressAction(self):
        pass

    def centerReleaseAction(self):
        pass

    def upPressAction(self):
        pass

    def upReleaseAction(self):
        pass

    def downPressAction(self):
        pass

    def downReleaseAction(self):
        pass

    def leftPressAction(self):
        pass

    def leftReleaseAction(self):
        pass

    def rightPressAction(self):
        pass

    def rightReleaseAction(self):
        pass

    """---Multi Direction Button End---"""

    """---Multi Function Button Start---"""

    def circlePressAction(self):
        pass

    def squarePressAction(self):
        pass

    def crossPressAction(self):
        pass

    def shutterPressAction(self):
        pass

    """---Multi Function Button End---"""

    """---Rotary Encoder Start---"""

    def rotaryEncoderClockwise(self):
        pass

    def rotaryEncoderCounterClockwise(self):
        pass

    def rotaryEncoderSelect(self):
        pass

    """---Rotary Encoder End---"""

    """---Communication Function Start---"""

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


if __name__ == '__main__':
    print(ControlledEnd.__doc__)
