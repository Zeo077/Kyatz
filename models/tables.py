from datetime import datetime
from time import mktime
import time

def get_email():
    if auth.user:
        return auth.user.email
    else:
        return 'None'

def get_username():
    if auth.user:
        return auth.user.username
    else:
        return 'None'

db.define_table('subscriptions',
	Field('usr', 'reference auth_user'),
	Field('c_id', 'reference comics'),
	Field('last_read', 'reference page_table')
	)

db.define_table('comments',
    Field('author', default = get_username()),
    Field('creation_date', 'datetime', default=datetime.utcnow()),
    Field('post_content', 'text'),
    Field('comic_id', 'reference comics'),
    Field('page_number', 'integer', default = 0),
    Field('upvote', 'integer', default = 0),
    Field('downvote', 'integer', default = 0),
    Field('rating', 'integer', default = time.time()),
    Field('h_level', 'integer', default = 0), #hierarchy level
    Field('parent', 'reference comments', default = 0),
    Field('edited','boolean',readable=False,writable=False,default=False),
    )

db.comments.author.writable = False
db.comments.id.readable = False
db.comments.creation_date.writable = False
db.comments.comic_id.readable = False
db.comments.comic_id.writeable = False
db.comments.page_number.readable = False
db.comments.page_number.writeable = False
db.comments.upvote.writable = False
db.comments.upvote.readable = False
db.comments.downvote.writable = False
db.comments.downvote.readable = False
db.comments.rating.writable = False
db.comments.rating.readable = False
db.comments.h_level.writable = False
db.comments.h_level.readable = False
db.comments.parent.writable = False
db.comments.parent.readable = False

db.define_table('votes',
    Field('user_id', 'reference auth_user'),
    Field('com_id', 'reference comments'),
    Field('vote_dir', 'boolean')
    )

db.define_table('comics',
    Field('title'),
    Field('author', default = None),
    Field('first_page', 'reference page_table'),
    Field('latest_page', 'reference page_table'),
    Field('num_pages', 'integer', default = 0),
    Field('RSS'),
    Field('thumbnail', default = None),
    Field('last_ping', 'datetime', default = datetime.utcnow()),
    )

#db.comics.author.writable = False
db.comics.id.readable = False
#db.comics.first_page.writable = False
db.comics.first_page.readable = False
#db.comics.latest_page.writable = False
db.comics.latest_page.readable = False
#db.comics.num_pages.writeable = False
db.comics.num_pages.readable = False
#db.comics.last_ping.writable = False
db.comics.last_ping.readable = False
#db.comics.RSS.writable = False
db.comics.RSS.readable = False
db.comics.thumbnail.readable = False

db.define_table('page_table',
    Field('comic', 'reference comics', readable=False),
    Field('page_number', 'integer', readable=False),
    Field('title'),
    Field('link', readable=False),
    Field('description', default = ''),
    Field('published', 'datetime'),
    )

db.define_table('tags',
    Field('tagname', default = None)
    )

db.define_table('tag2comment',
    Field('tag_id', 'reference tags'),
    Field('comment_id', 'reference comments')
    )

db.define_table('tag2comic',
    Field('tag_id', 'reference tags'),
    Field('comic_id', 'reference comics')
    )
    
import datetime
import gluon.contrib.rss2 as rss2
import gluon.contrib.feedparser as feedparser

def t_to_dt(t):#time_to_datetime
    if(t):
        return datetime.fromtimestamp(mktime(t))
    else:
        return None
def update_com(i):
    comic = db.comics(i)
    link = comic.RSS
    if(link):
        d = feedparser.parse(link)
        entries = sorted(d.entries, key=lambda e:e.get('published_parsed'))
        for entry in entries:
            if not (db((db.page_table.comic == comic) & (db.page_table.title == entry.title)).select().first()):
                num = comic.num_pages + 1
                comic.update_record(num_pages=num)
                t = t_to_dt(entry.get('published_parsed')) or datetime.utcnow()
                db.page_table.insert(
                    comic = comic,
                    page_number = num,
                    title = entry.get('title'),
                    link = entry.get('link'),
                    description = entry.get('description'),
                    published = t,#entry.get('published_parsed', datetime.utcnow()),
                    )
        first = db(db.page_table.title==entries[0].title).select().first()
        last = db(db.page_table.title==entries[-1].title).select().first()
        comic.update_record(first_page=first,latest_page=last)
    redirect(URL('default','index'))

def repair_comic(i):
    comic = db.comics(i)
    rows = db(db.page_table.comic==comic).select(orderby=db.page_table.published)
    comic.update_record(num_pages=len(rows))
    num = 1
    for row in rows:#rows.sort(lambda r: r.published.datetime):
        row.update_record(page_number = num)
        num += 1

    # prototype rating weight: each upvote/downvote is equal to one hour
    # this will likely become something more like an exponential scaling function later
def plusvote(comment_id):
    c = db.comments(comment_id)
    c.update_record(upvote=c.upvote+1,rating=c.rating-session.hour)
    '''c.upvote = c.upvote + 1
    c.rating = c.rating - session.hour
    c.update()'''

def minusvote(comment_id):
    c = db.comments(comment_id)
    c.update_record(downvote = c.downvote+1,rating=c.rating+session.hour)
    '''c.downvote = c.downvote + 1
    c.rating = c.rating + session.hour
    c.update()'''

def plusvote_remove(comment_id):
    c = db.comments(comment_id)
    c.update_record(upvote=c.upvote-1,rating=c.rating+session.hour)

def minusvote_remove(comment_id):
    c = db.comments(comment_id)
    c.update_record(downvote = c.downvote-1,rating=c.rating-session.hour)
    
db.define_table('test_db',
    Field('test'),
    )

#def insert_page(comic, entry):

#def read_entries(comic, entries):
#    rows = db(db.pages.comic == comic) or False
