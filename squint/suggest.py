import argparse, math
from raddoo import partition, pluck
from squint.db import db, model, sql


parser = argparse.ArgumentParser(
    description="Rate a piece of content given a user's pubkey and event id.")

parser.add_argument('user', help="User pubkey")
parser.add_argument('event', help="Event id")

args = parser.parse_args()

scores = {
    '-': -1, '+': 1, '🌲': 0.1, '🍊': 0.1, '🎉': 1, '👀': 0.5, '👆': 1, '👍': 1, '💚': 1, '💡': 0.5,
    '💯': 1, '🖖': 0.5, '😂': 0.5, '😄': 0.5, '😆': 0.5, '🙏': 0.5, '🚀': 1, '🤣': 0.5, '🤦': -0.5,
    '😍': 1,
}


def avg(xs):
    return sum(xs) / len(xs) if xs else 0


with db.transaction():
    # Find people we follow
    follows = set([
        t[1] for t in model.val('event', 'tags', where={'pubkey': args.user, 'kind': 3})
    ])

    # Find reactions to the event
    follow_reactions, global_reactions = partition(
        lambda r: r['pubkey'] in follows,
        filter(
            lambda r: r['content'] in scores,
            model.all(
                'event',
                select=['content', 'pubkey'],
                where=sql.sql("where tags::text ~* {} and kind = 7 and content != ''").format(sql.literal(args.event))
            )
        )
    )

    print(len(global_reactions))
    print(len(follow_reactions))

    global_rating = avg([scores[r] for r in pluck('content', global_reactions)])
    follow_rating = avg([scores[r] for r in pluck('content', follow_reactions)])
    total_rating = avg([global_rating, follow_rating, follow_rating])

    __import__("pprint").pprint([global_rating, follow_rating, total_rating])
