'''

'''
from functools import wraps


def save_headers(func):
    @wraps(func)  # We don't want to lose our method name
    def inner_method(*args, **kwargs):
        request = args[1] if len(args) > 1 else args[0]  # Deal with function anc Class-Based views
        user = request.user

        return func(*args, **kwargs)
    return inner_method