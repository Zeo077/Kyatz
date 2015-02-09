from datetime import datetime
import gluon.contrib.rss2 as rss2
import gluon.contrib.feedparser as feedparser

def redirect_home():
    redirect(URL('default','index'))

def index():
    if(auth.user):
        if(auth.user.username == 'admin'):
            redirect(URL('default', 'admin', user_signature=True))
    return dict()

@auth.requires_signature()
def admin():
    grid=SQLFORM.grid(db.comics)
    return dict(grid=grid)    

def browse():
    q = db.comics.id > 0
    if not db(q).isempty():
        disp = SQLFORM.grid(query=q, fields=[db.comics.title,db.comics.author], details=False, editable=False, deletable=False, csv=False, create=False,
                links=[dict(header=T(''), body = lambda r: A(T('Comments'), _class='btn', _href=URL('default', 'thread', args=[r.id,0]))),
                    dict(header=T(''),body= lambda r: A(T('Pages'), _class='btn',_href=URL('default','comic_pages',args=r.id))),
                    dict(header=T(''), body = lambda r: toggle_comic(r.id)),
                ]
            )
    else:
        disp = "No comics were found in the database.\nPlease contact site administrators."
    return dict(disp=disp)

def toggle_comic(c):
    if(auth.user):
        subs = db.auth_user(auth.user_id).subscribed
        if(c in subs):
            link = A(T('Unsubscribe'), _class='btn', _href=URL('default','unsubscribe',args=c))#link = T('Subscribed')
        else:
            link = A(T('Subscribe'), _class='btn',_href=URL('default','subscribe',args=c))
    else:
        link = A(T('Subscribe'), _class='btn',_href=URL('default','subscribe',args=c))
    return link

@auth.requires_login()
def subscribe():
	if request.args:
		c_id = int(request.args[0])
	else:
		redirect(URL('default','browse'))
	subs = db.auth_user(auth.user_id).subscribed
	subs.append(c_id)
	db.auth_user(auth.user_id).update_record(subscribed=subs)
	db.subscriptions.insert(usr=auth.user_id, c_id=c_id, last_read=0)
	redirect(URL('default','browse'))

@auth.requires_login()
def unsubscribe():
    if request.args:
        c_id = int(request.args[0])
    else:
        redirect(URL('default','browse'))
    subs = db.auth_user(auth.user_id).subscribed
    if c_id in subs:
        subs.remove(c_id)
        db.auth_user(auth.user_id).update_record(subscribed=subs)
    if(request.args < 2):
        redirect(URL('default','browse'))
    else:
        redirect(URL('default',request.args[1]))

def comic_pages():
    if(request.args):
        q = db.page_table.comic == request.args[0]
    else:
        redirect(URL('default','browse'))
    if not db(q).isempty():
        disp = SQLFORM.grid(query=q, fields=[db.page_table.comic,db.page_table.page_number,db.page_table.title,db.page_table.link,db.page_table.published], details=False, editable=False, deletable=False, csv=False, create=False, user_signature=False,
                links=[dict(header=T(''), body = lambda r: A(T('Comments'), _class='btn', _href=URL('default', 'thread', args=[r.comic,r.page_number]))),
                    dict(header=T(''), body = lambda r: A(T('View Comic'), _class='btn', _href=URL('default', 'goto_page', args=[r.comic, r.page_number]))),
                ]
            )
        comic = db.comics(int(request.args[0]))
        return dict(disp=disp,comic=db.comics(request.args[0]).title,img=comic.get('thumbnail', None))
    else:
        return HTML(BODY(H1(T('No pages found.')))).xml() 

def comment():
    if(len(request.args)>1):
        comic = db.comics(request.args[0])
        page = db(db.page_table.page_number==request.args[1]).select().first()
        if(len(request.args)>2):
            parent = db.comments(request.args[2])
        else:
            parent = None
    elif(request.args):
        comic = db.comics(request.args[0])
        page = None
        parent = None
    else:
        redirect(URL('default','index'))
    form = SQLFORM.factory(
        Field('comment','text'),
        Field('comic','reference comic',readable=False,writable=False),
        Field('page','reference page_table',readable=False,writable=False),
        Field('parent','reference comments',readable=False,writable=False),
        )
    form.vars.comic=comic.id
    if(page):
        form.vars.page=page.id
    else:
        form.vars.page = 0
    form.vars.parent=parent
    if form.process().accepted:
        if(form.vars.parent):
            parent = form.vars.parent
            h_level = parent.h_level + 1
        else:
            h_level = 0
            parent = 0
        db.comments.insert(
            author=get_username(),
            #creation_date=datetime.utcnow(),
            post_content=form.vars.comment,
            comic_id=form.vars.comic,
            page_number=form.vars.page,
            #upvote=0,
            #downvote=0,
            #rating=time.time(),
            h_level=h_level,
            parent=parent
            )
        args = []
        if(form.vars.comic): 
            args += [form.vars.comic]
        if(form.vars.page or form.vars.page==0):
            args += [form.vars.page]
        if(form.vars.parent):
            args += [parent.id]
        redirect(URL('default','thread',args=args))
    return dict(form=form)

@auth.requires_login()
def subscriptions():
    grid = SQLFORM.grid(db.comics.id.belongs(db.auth_user(auth.user_id).subscribed),
        details=False, editable=False, deletable=False, csv=False, create=False,
        links=[dict(header=T(''), body = lambda r: A(T('Unsubscribe'), _class='btn', _href=URL('default','unsubscribe',args=[r.id,'subscriptions'])) )]
        )
    return dict(grid=grid)

@auth.requires_login()
def updates():
    return dict(subs=db.auth_user(auth.user_id).subscribed)

@auth.requires_signature()
def goto_page():
    if(len(request.args)>1):
        c_id = request.args[0]
        p_num = request.args[1]
    elif(request.args):
        redirect(URL('default', 'comic_pages', args=request.args[0])) 
    else:
        redirect(URL('default', 'browse'))   
    q = (db.page_table.comic == c_id) & (db.page_table.page_number == p_num)
    current_page = db(q).select().first()
    q2 = (db.subscriptions.usr == auth.user_id) & (db.subscriptions.c_id == c_id)
    sub = db(q2).select().first()
    if(sub):
        last_read = db.page_table(sub.last_read)
        if(last_read):
            if(last_read.page_number < current_page.page_number):
                sub.update_record(last_read=current_page.id)
        else:
            sub.update_record(last_read=current_page.id)
    elif(c_id in db.auth_user(auth.user_id).subscribed):
        db.subscriptions.insert(usr=auth.user_id, c_id=c_id, last_read=current_page.id)
    redirect(current_page.link)

@auth.requires_signature()
def clear():
    if auth.user:
        url = URL('default','updates')
        if request.args:
            c_id = int(request.args[0])
            sub = db((db.subscriptions.usr == auth.user_id) & (db.subscriptions.c_id == c_id)).select().first()
            if sub:
                comic = db.comics(c_id)
                latest_page = comic.latest_page
                sub.update_record(last_read=latest_page)
    else:
        url = URL('default','index')
    redirect(url)

#d = feedparser.parse("http://feeds.feedburner.com/SchlockRSS?format=xml")
#http://feeds.feedburner.com/DuelingAnalogs?format=xml
#http://latchkeykingdom.smackjeeves.com/rss/
def rss():
    if(request.args):
        link = request.args[0]
    else:
        link = "http://latchkeykingdom.smackjeeves.com/rss/"
    import datetime
    import gluon.contrib.rss2 as rss2
    import gluon.contrib.feedparser as feedparser
    #d = feedparser.parse('http://rss.slashdot.org/Slashdot/slashdot/to')
    #d = feedparser.parse("http://feeds.feedburner.com/SchlockRSS?format=xml")
    d = feedparser.parse("http://latchkeykingdom.smackjeeves.com/rss/")
    logger.info(d)
    for entry in d.entries:
        logger.info(entry)
        logger.info(entry.published)
    logger.info("<<<>>>end")
    rss = rss2.RSS2(title=d.channel.title, link=d.channel.link,
                    description=d.channel.description,
                    lastBuildDate=datetime.datetime.now(),
                    items=[rss2.RSSItem(title=entry.title,
                    link=entry.link, description=entry.description,
                    pubDate=datetime.datetime.now()) for entry in
                    d.entries])
    response.headers['Content-Type'] = 'application/rss+xml'
    return rss.to_xml(encoding='utf-8')

def edit_comic():
    if request.args:
        i = request.args[0]
    else:
        raise HTTP(404)
    form = SQLFORM(db.comics, record = i)
    if form.process().accepted:
        #redirect(URL('default','index'))
        redirect(URL('default','update_comic',args=i))
    return dict(form=form)

def update_comic():
    if(request.args):
        i = request.args[0]
    else:
        redirect(URL('default','index'))
    update_com(i)

def repair_page_numbers():
    if(request.args):
        i = request.args[0]
    else:
        redirect_home()
    repair_comic(i)
    redirect_home()

def import_rss():
    form = SQLFORM.factory(
        Field('link', requires=IS_URL()),
        )
    if form.process().accepted:
        d = feedparser.parse(form.vars.link)
        i = db.comics.insert(title = d.feed.get('title'),RSS=form.vars.link)
        redirect(URL('default','edit_comic',args=i))
    return dict(form=form)
    
def insert_page():
    if(request.args):
        i = request.args[0]
    else:
        redirect_home()
    form = SQLFORM.factory(
        Field('title'),
        Field('link'),
        Field('published', 'datetime', default=datetime.utcnow()),
        hidden=dict(comic=i)
        )
    if form.process().accepted:
        db.page_table.insert(comic=form.vars.comic,title=form.vars.title,link=form.vars.link,published=form.vars.published)
        repair_comic(form.vars.comic)
        redirect_home()
    returrn(form=form)


def view():
    f = db(db.files.file_url==request.args(0)).select()[0].id
    form = SQLFORM(db.board, record = f, readonly=True)
    fid = db(db.files.file_url==request.args(0)).select()[0].file_id
    return dict(form=form, post_content=db(db.board.id==fid).select()[0].post_content)

def display():
    return generate_comments(0,0)#dict(comments=generate_comments(-1,-1))

def hash_id(s):
    l = len(s)
    num = 0
    count = 0
    for c in s:
        num += ord(c) * (31 ** (l-1-count))
        count += 1
    return hex(num)[2:]

# BEGIN COMMENT THREAD STUFF

# Time object = seconds since epoch
session.hour = 60*60

def gen_post(row, c_id, p_num, h_level):
    p =  'Author: '+row.author+' Time: '+str(row.creation_date) + ' V: +' + str(row.upvote) + ' -' + str(row.downvote)
    if(row.edited):
        p = '* '+ p
    #p += '\n\n'
    #p += row.post_content
    q1 = db.comments.comic_id == c_id
    q2 = db.comments.page_number == p_num
    q3 = db.comments.h_level == h_level
    query = q1 & q2 & q3
    rows = db(query).select()
    
    up_button = A(T('up'), _class='btn',_href=URL('default','upvote',args=row.id))
    down_button = A(T('down'), _class='btn',_href=URL('default','downvote',args=row.id))
    edit_button = A(T('edit'), _class='btn',_href=URL('default','edit_comment',args=row.id,user_signature=True))
    par = P(p) + P(row.post_content) + A(T('comment'), _class='btn',_href=URL('default','comment',args=[c_id,p_num,row.id])) + up_button + down_button
    if(row.author == get_username()):
        par += edit_button
    
    for r in rows.sort(lambda r: r.rating):
        if(row.id == r.parent):
            par += gen_post(r, c_id, p_num, h_level+1)
    return TABLE(TR(TD(par)), _border='1', _width="100%")

def thread():
    if request.args:
        c_id = 0
        try:
            c_id = int(request.args[0])
        except ValueError:
            c_id = 0
        if(len(request.args)>1):
            p_num = 0
            try:
                p_num = int(request.args[1])
            except ValueError:
                p_num = 0
        else:
            p_num = 0
    else:
        redirect(URL('default','index'))

    img = db.comics(c_id).get('thumbnail',None)
    q1 = db.comments.comic_id == c_id
    q2 = db.comments.page_number == p_num
    q3 = db.comments.h_level == 0
    query = q1 & q2 & q3
    rows = db(query).select()
    a = 0
    post = None
    for row in rows.sort(lambda row: row.rating):
        if(post == None):
            post = gen_post(row, c_id, p_num, 1)
        else:
           post = post + gen_post(row, c_id, p_num, 1)
    if not post:
        post = T('No comments found')
    comic = db.comics(c_id)
    c_string = comic.title
    title = H1(A(c_string, _href=db.page_table(comic.first_page).link))
    if(p_num > 0):
        page = db(db.page_table.page_number==p_num).select().first()
        p_string = page.title
        title += H4(A(p_string, _href=page.link))
    args = []
    if(c_id>0):
        args += [c_id]
        if(p_num>0):
            args += [p_num]
    backbutton = None
    nextbutton = None
    if(p_num != 0):
        backbutton = A('< Previous', _href=URL('thread',args=[c_id,p_num-1]), _class='btn')
    if(p_num != comic.num_pages):
        nextbutton = A('Next >', _href=URL('thread',args=[c_id,p_num+1]), _class='btn')
    return dict(post=post, title=title, args=args, img=img, back_btn=backbutton, next_btn=nextbutton)

@auth.requires_login()
def upvote():
    if request.args:
        com_id = int(request.args[0])
        db.votes(com_id)
        comment = db.comments(com_id)
        q = (com_id == db.votes.com_id) & (auth.user.id == db.votes.user_id)
        r = db(q).select().first()
        if(r):
            if(r.vote_dir == 1):
                redirect(URL('default','thread',args=[comment.comic_id,comment.get('page_number',0)]))
            else:
                minusvote_remove(com_id)
                r.update_record(vote_dir = 1)
        else:
            db.votes.insert(user_id = auth.user.id, com_id = com_id, vote_dir = 1)
        plusvote(com_id)
        redirect(URL('default','thread',args=[comment.comic_id,comment.get('page_number',0)]))
    else:
        redirect(URL('default','browse'))

@auth.requires_login()
def downvote():
    if request.args:
        com_id = int(request.args[0])
        comment = db.comments(com_id)
        q = (com_id == db.votes.com_id) & (auth.user.id == db.votes.user_id)
        r = db(q).select().first()
        if(r):
            if(r.vote_dir == 0):
                redirect(URL('default','thread',args=[comment.comic_id,comment.get('page_number',0)]))
            else:
                plusvote_remove(com_id)
                r.update_record(vote_dir = 0)
        else:
            db.votes.insert(user_id = auth.user.id, com_id = com_id, vote_dir = 0)
        minusvote(com_id)
        redirect(URL('default','thread',args=[comment.comic_id,comment.get('page_number',0)]))
    else:
        redirect(URL('default','browse'))

@auth.requires_signature()
def edit_comment():
    if(request.args == None):
        redirect(URL('default','browse'))
    com_id = int(request.args[0])
    form = SQLFORM(db.comments,db.comments(com_id))
    form.vars.edited = True
    #form.vars.comic_id.writable = False
    #form.vars.page_number.writable = False
    #form.vars.upvote.readable = False
    #form.vars.downvote.readable = False
    if form.process().accepted:
        redirect(URL('default','thread',args=[form.vars.comic_id,form.vars.page_number]))#redirect(URL('default','thread',args=[]))
    return dict(form=form)
        
# END COMMENT THREAD STUFF
    
def user():
    """
    exposes:
    http://..../[app]/default/user/login
    http://..../[app]/default/user/logout
    http://..../[app]/default/user/register
    http://..../[app]/default/user/profile
    http://..../[app]/default/user/retrieve_password
    http://..../[app]/default/user/change_password
    http://..../[app]/default/user/manage_users (requires membership in
    use @auth.requires_login()
        @auth.requires_membership('group name')
        @auth.requires_permission('read','table name',record_id)
    to decorate functions that need access control
    """
    return dict(form=auth())

@cache.action()
def download():
    """
    allows downloading of uploaded files
    http://..../[app]/default/download/[filename]
    """
    return response.download(request, db)


def call():
    """
    exposes services. for example:
    http://..../[app]/default/call/jsonrpc
    decorate with @services.jsonrpc the functions to expose
    supports xml, json, xmlrpc, jsonrpc, amfrpc, rss, csv
    """
    return service()


@auth.requires_signature()
def data():
    """
    http://..../[app]/default/data/tables
    http://..../[app]/default/data/create/[table]
    http://..../[app]/default/data/read/[table]/[id]
    http://..../[app]/default/data/update/[table]/[id]
    http://..../[app]/default/data/delete/[table]/[id]
    http://..../[app]/default/data/select/[table]
    http://..../[app]/default/data/search/[table]
    but URLs must be signed, i.e. linked with
      A('table',_href=URL('data/tables',user_signature=True))
    or with the signed load operator
      LOAD('default','data.load',args='tables',ajax=True,user_signature=True)
    """
    return dict(form=crud())
