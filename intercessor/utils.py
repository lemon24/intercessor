from __future__ import print_function


try:
    input = raw_input
except NameError:
    input = input


def prompt(text):
    try:
        return input(text)
    except EOFError:
        print()
        raise
    except KeyboardInterrupt:
        print('^C')
        raise


def confirm(text, default=False):
    options = "Y/n" if default else "y/N"
    try:
        rv = input("{} [{}]: ".format(text, options))
        rv = rv.strip().lower()
        if not rv:
            return default
        return rv == 'y'
    except EOFError:
        print('y' if default else 'n')
        return default
    except KeyboardInterrupt:
        print('^C')
        return not default


def echo(*args, **kwargs):
    print(*args, **kwargs)

