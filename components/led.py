import wiringpi

import configLoader

config = configLoader.ConfigLoader('./config.json')
green, blue = config['led']['led_green'], config['led']['led_blue']
state = {
    green: 1,
    blue: 1
}

wiringpi.wiringPiSetup()
wiringpi.pinMode(green, 1)
wiringpi.pinMode(blue, 1)
wiringpi.digitalWrite(green, state[green])
wiringpi.digitalWrite(blue, state[blue])


def toggleState(led):
    state[led] = not state[led]
    wiringpi.digitalWrite(led, state[led])


def on(led):
    state[led] = 0
    wiringpi.digitalWrite(led, state[led])


def off(led):
    state[led] = 1
    wiringpi.digitalWrite(led, state[led])


if __name__ == '__main__':
    pass
    '''on(blue)
    off(green)
    time.sleep(1)
    on(green)
    off(blue)'''
