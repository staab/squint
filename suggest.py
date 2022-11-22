import argparse, math, json, asyncio, websockets, time
from raddoo import (
    partition, pluck, last, pick_values, random_uuid, ichunk, first, without, pick,
    group_by, sort_by, prop)


parser = argparse.ArgumentParser(description="Suggest content for given user.")
parser.add_argument('pubkey', help="User pubkey")

since = int(time.time()) - 60 * 60 * 24 * 30
url = 'wss://nostr-pub.wellorder.net'
chunk_size = 100
scores = {
    '-': -1, '+': 1, '🌲': 0.1, '🍊': 0.1, '🎉': 1, '👀': 0.5, '👆': 1, '👍': 1, '💚': 1, '💡': 0.5,
    '💯': 1, '🖖': 0.5, '😂': 0.5, '😄': 0.5, '😆': 0.5, '🙏': 0.5, '🚀': 1, '🤣': 0.5, '🤦': -0.5,
    '😍': 1,
}


async def main(pubkey):
    # Find our follows
    own_follows = set([
        t[1] async for e in req(url, {'authors': [pubkey], 'kinds': [3]})
        for t in e['tags']
    ])

    # Find people who our follows follow too
    transitive_follows = set([
        t[1] async for e in req(url, {'authors': list(own_follows), 'kinds': [3]})
        for t in e['tags']
    ])

    all_follows = own_follows.union(transitive_follows)

    # Get recent notes
    all_notes = []
    all_reactions = []

    for i, chunk in enumerate(ichunk(chunk_size, all_follows)):
        print(f"Downloading chunk {i}/{int(len(all_follows)/chunk_size)}")

        all_notes.extend([
            prune_event(e) async for e in req(url, {
                'kinds': [1],
                'since': since,
                'authors': list(chunk),
            })
        ])

        all_reactions.extend([
            prune_event(e) async for e in req(url, {
                'kinds': [7],
                'since': since,
                'authors': list(chunk),
            })
        ])

    # Get recent reactions, group them by event id
    reactions_by_event = group_by(lambda e: e['tags'][0][1], all_reactions)

    # Keep a running score for accounts
    accounts = {}
    for note in all_notes:
        accounts.setdefault(note['pubkey'], [0, 0])
        account_notes, account_rating = accounts[note['pubkey']]

        follow_reactions, global_reactions = partition(
            lambda r: r['pubkey'] in own_follows,
            reactions_by_event.get(note['id'], [])
        )

        follow_reaction_chars = [s for r in pluck('content', follow_reactions) for s in r if len(r) < 5]
        global_reaction_chars = [s for r in pluck('content', global_reactions) for s in r if len(r) < 5]

        follow_rating = avg([scores[s] for s in follow_reaction_chars if s in scores])
        global_rating = avg([scores[s] for s in global_reaction_chars if s in scores])

        # Calculate the post rating based on account rating, and reactions weighted toward
        # people we follow. Note reactions and account rating for display
        note['rating'] = avg([account_rating, global_rating, follow_rating, follow_rating])
        note['reactions'] = [follow_reaction_chars, global_reaction_chars]
        note['account_rating'] = account_rating

        # Incorporate the note's rating into the average account rating
        accounts[note['pubkey']] = [
            account_notes + 1,
            (account_rating * account_notes + note['rating']) / (account_notes + 1)
        ]

    print("Recommended posts:")
    for e in list(reversed(sort_by(prop.c('rating'), all_notes)))[:10]:
        print("\n----------")
        print(f"Link: https://astral.ninja/event/{e['id']}")
        print('Rating:', e['rating'], "Account Rating:", e['account_rating'], "Follows:", ''.join(e['reactions'][0]), "Other:", ''.join(e['reactions'][1]))
        print(e['content'])


async def req(url, query):
    async with websockets.connect(url) as ws:
        await ws.send(json.dumps(["REQ", random_uuid(), query]))

        while True:
            type, *raw = json.loads(await ws.recv())

            if type == 'EOSE':
                break

            yield last(raw)


def avg(xs):
    return sum(xs) / len(xs) if xs else 0


def prune_event(e):
    return pick(['id', 'pubkey', 'kind', 'content', 'tags'], e)


if __name__ == '__main__':
    args = parser.parse_args()

    asyncio.run(main(args.pubkey))
