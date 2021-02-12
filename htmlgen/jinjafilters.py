import html


def seconds_to_string(n):
    if n is None or not isinstance(n, int):
        return ""
    SECSINMIN = 60
    SECSINHOUR = SECSINMIN * 60
    HOURSINDAY = 24
    SECSINDAY = HOURSINDAY * SECSINHOUR
    d = n // SECSINDAY
    n %= SECSINDAY
    h = n // SECSINHOUR
    n %= SECSINHOUR
    m = n // SECSINMIN
    n %= SECSINMIN
    if d > 0:
        return f"{d:02}.{h:02}:{m:02}:{n:02}"
    return f"{h:02}:{m:02}:{n:02}"

def winner(value):
    if value == "00:00:00":
        return "Winner"
    return value


def htmlescape(value):
    return html.escape(value)

def zero_empty_string(value):
    if not value:
         return ""
    return value

def add_or_empty(value, v):
    if isinstance(value, int):
        return value + v
    return ""

def empty_if_true(value, b):
    if b:
        return ""
    return value

def sortable(value):
    if not value:
        return 300
    return ord(value[0])

class FilterModule(object):

    def filters(self):
        return {
            'timestr': seconds_to_string
        }