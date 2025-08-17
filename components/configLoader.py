import json

class ConfigLoader:
    _instance = None  
    
    def __new__(cls, configPath='./config.json'):
        # 如果实例不存在，则创建新实例
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            with open(configPath) as f:
                cls._instance.__config = json.load(f)
        return cls._instance
    
    def __getitem__(self, item):
        return self.__config[item]
    
if __name__=='__main__':
    print(ConfigLoader()['pin'])