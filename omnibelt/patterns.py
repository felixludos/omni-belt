
class InitWall:
    def __init__(self, *args, _req_args=(), _req_kwargs={}, **kwargs):
        super().__init__(*_req_args, **_req_kwargs)


class Singleton(object):
    _instance = None
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance


class InitSingleton(Singleton):
    _instance_initialized = False
    
    def __init__(self, *args, **kwargs):
        if not self.__class__._instance_initialized:
            self.__class__._instance_initialized = True
            self.__init_singleton__(*args, **kwargs)
    
    def __init_singleton__(self, *args, **kwargs):
        pass







