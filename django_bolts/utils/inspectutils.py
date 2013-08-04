

__all__ = ['get_subclasses']

def get_subclasses(cls):
    return cls.__subclasses__() + [g for s in cls.__subclasses__()
                                   for g in get_subclasses(s) ]
