class Singleton(type):
    """
    Assists in the creation of Singleton classes.  To make use of the singleton class:

    from common.singleton import Singleton

    ...
    ...
    class SomeClass(object):
        __metaclass__ = Singleton
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

    def purge(cls):
        """
        Helper function to remove an instance from the class-map
        This method allows a unittest to clear an existing map if
        it exists.
        :param cls: class to remove from class->instance map
        :type cls: class using Singleton is __metaclass__
        :return: None
        :rtype: None
        """
        if cls in Singleton._instances:
            del Singleton._instances[cls]
