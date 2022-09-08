
class InitWall:
    def __init__(self, *args, _multi_inits=None, _req_args=(), _req_kwargs={}, **kwargs):
        if _multi_inits is None:
            super().__init__(*_req_args, **_req_kwargs)
        else:
            for base in _multi_inits:
                if base is None:
                    super().__init__(*_req_args.get(base, ()),
                                     **_req_kwargs.get(base, {}))

                elif isinstance(self, base):
                    super(base, self).__init__(*_req_args.get(base,()),
                                               **_req_kwargs.get(base, {}))


class Singleton(object):
    _instance = None
    
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance


# class InitSingleton(Singleton):
#     _instance_initialized = False
#
#     def __init__(self, *args, **kwargs):
#         if not self.__class__._instance_initialized:
#             self.__class__._instance_initialized = True
#             self.__init_singleton__(*args, **kwargs)
#
#     def __init_singleton__(self, *args, **kwargs):
#         pass







