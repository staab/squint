import json, asyncio, websockets
from psycopg2.errors import UniqueViolation
from raddoo import last, pick_values, random_uuid, ichunk
from squint.db import db, model


def req(payload):
    return json.dumps(["REQ", random_uuid(), payload])


async def sync(url, query):
    async with websockets.connect(url) as ws:
        await ws.send(req({'kinds': [1, 3, 7], **query}))

        while True:
            type, *raw = json.loads(await ws.recv())

            if type == 'EOSE':
                break

            event = last(raw)

            # Ignore DMs
            if event['kind'] in {4}:
                continue

            try:
                with db.transaction():
                    model.insert('event', event)
            except UniqueViolation as e:
                pass

url = 'wss://nostr-pub.wellorder.net'
pubkey = "97c70a44366a6535c145b333f973ea86dfdc2d7a99da618c40c64705ad98e322"
chunk_size = 500

if False:
    # Sync events created by this public key
    asyncio.run(sync(url, {'authors': [pubkey]}))

    # Sync events created by people we follow
    with db.transaction():
        follows = list(set([
            t[1] for t in model.val('event', 'tags', where={'pubkey': pubkey, 'kind': 3})
        ]))

    asyncio.run(sync(url, {'authors': follows}))

    # sync events related to reactions
    with db.transaction():
        events = list(set([
            t[1] for row in model.col('event', 'tags', where={'kind': 7}) for t in row
        ]))

    for chunk in ichunk(chunk_size, events):
        asyncio.run(sync(url, {'ids': chunk}))

# Find all reactions related to kind 1 events
with db.transaction():
    events = list(set(model.col('event', 'id', where={'kind': 1})))

for chunk in ichunk(chunk_size, events):
    asyncio.run(sync(url, {'#e': chunk, 'kind': 7}))
