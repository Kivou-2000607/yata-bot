# import standard modules
import json
import asyncio
import re
import os
import asyncpg


async def get_member_key(member=None, tornId=None, needPerm=True):
    """ get a member key from YATA database
        return status, tornId, Name, key
        return 0, id, Name, Key: All good
        return -1, None, None, None: did not parse torn id from display name
        return -2, id, None, None: did not find torn id in yata db
        return -3, id, Name, None: member did not give perm
    """

    # Need at least a member or an id
    if tornId is None and member is None:
        print("get_member_key needs at least a member or a tornId")
        exit()

    # get torn id from name
    if tornId is None and member is not None:
        match = re.match(r'([a-zA-Z0-9_-]{1,16}) \[(\d{1,7})\]', member.display_name)
        if match is not None:
            tornId = int(member.display_name.split("[")[-1][:-1])
        else:
            return -1, None, None, None

    # get YATA user
    db_cred = json.loads(os.environ.get("DB_CREDENTIALS"))
    dbname = db_cred["dbname"]
    del db_cred["dbname"]
    con = await asyncpg.connect(database=dbname, **db_cred)
    user = await con.fetch(f'SELECT "tId", "name", "key", "botPerm" FROM player_player WHERE "tId" = {tornId};')
    await con.close()

    # user not on YATA
    if not len(user):
        return -2, tornId, None, None

    # make req[0] a tuple
    user = tuple(user[0])

    # user didn't give permission
    if not user[3] and needPerm:
        return -3, user[0], user[1], None

    # return id, name, key
    else:
        return 0, user[0], user[1], user[2]
