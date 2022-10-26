
from .typing import unspecified_argument


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



class Service:
    _service_cls = None
    _server_cls = None
    def __init_subclass__(cls, use=False, server=unspecified_argument, **kwargs):
        super().__init_subclass__(**kwargs)
        if server is unspecified_argument:
            server = cls
        if cls._service_cls is None:
            cls._service_cls = server
            cls._service_cls._server_cls = server
        elif use:
            cls._service_cls._server_cls = cls


    def __new__(cls, *args, **kwargs):
        if cls._service_cls is None:
            return super().__new__(cls)
        else:
            return cls._service_cls._server_cls(*args, **kwargs)



