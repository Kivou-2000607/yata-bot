from datetime import datetime

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


def log_fmt(log, headers=dict({}), traceback=None):
    lst = ['```md']
    if len(headers):
        lst.append('# headers')
        for k, v in headers.items():
            lst.append(f'> {k:<16} {v}')
        lst.append('')
    lst.append('# error message')
    lst.append(f'{log}')
    if traceback is not None:
        lst.append('\n# full message')
        lst.append(f'{traceback}')
    lst.append('```')
    return "\n".join(lst)
