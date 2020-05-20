from datetime import datetime
import traceback
import re

def permissions_rsm(permissions):
    perm = []
    if permissions.read_messages:
        perm.append('R')
    if permissions.send_messages:
        perm.append('S')
    if permissions.manage_messages:
        perm.append('M')
    return '/'.join(perm)


def now():
    return datetime.utcnow()

def ts_now():
    return datetime.timestamp(datetime.utcnow())

def ts_format(timestamp, fmt=None):
    d = datetime.fromtimestamp(timestamp, tz=pytz.UTC)
    if fmt == "time":
        return d.strftime("%H:%M:%S")
    elif fmt == "short":
        return d.strftime("%m/%d %H:%M:%S")
    else:
        return d

def hide_key(error):
    return f"{error}" if re.search('api.torn.com', f'{error}') is None else "API's broken... #blamched"

def log_fmt(error, headers=dict({}), full=False):
    lst = ['```md']

    # headers
    if len(headers):
        lst.append('# headers')
        for k, v in headers.items():
            if isinstance(v, list):
                lst.append(f'> {k:<16} {", ".join(v)}')
            else:
                lst.append(f'> {k:<16} {v}')
        lst.append('')

    # error message
    if len(headers) or full:
        lst.append('# error message')
    errorMSG = hide_key(error)
    lst.append(f'{errorMSG}')

    # traceback
    if full:
        tb = "\n".join([line[:-2] for line in traceback.format_exception(type(error), error, error.__traceback__)])
        tb = hide_key(tb)
        lst.append('\n# full message')
        lst.append(f'{tb}')

    lst.append('```')
    return "\n".join(lst)
