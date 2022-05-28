import json


class ConfigLoader:
    def __init__(self, configPath):
        with open(configPath) as f:
            self.__config = json.load(f)

    def __getitem__(self, item):
        return self.__config[item]
