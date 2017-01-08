# encoding=utf8
import base64
import datetime
import hashlib
import hmac
import json
import os
import random
import re
import sqlite3
import struct
import sys
import textblob
import time
import urllib
import weechat

reload(sys)
sys.setdefaultencoding('utf8')

weechat.register("hankbot", "ceph", "2.7.1", "GPL3", "hankbot", "", "")

def get_hank_home():
    infolist = weechat.infolist_get("python_script", "", "hankbot")
    fname = "~/hank/hank.py"
    while weechat.infolist_next(infolist):
        fname = weechat.infolist_string(infolist, "filename")
    weechat.infolist_free(infolist)
    return os.path.dirname(os.path.realpath(fname))

HANK_HOME = get_hank_home()
IMGUR_CLIENT_ID = "fe0966af56cc0f0"
IMGUR_CLIENT_SECRET = "cf14e4b09a9ae536ce21fc235e2f310fc97968f2"
YOUTUBE_API_KEY = "AIzaSyAiYfOvXjvhwUFZ1VPn696guJcd2TJ-Lek"
SQLITE_DB = HANK_HOME + "/hank.db"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, " \
    "like Gecko) Chrome/47.0.2526.106 Safari/537.36"
UNPROVOKED_ODDS = 75
UNPROVOKED_SHOUT_ODDS = 20
UNPROVOKED_IMPOSSIBLE_ODDS = 9999
ROSS_ODDS = 5
PROVOKED_ODDS = 5
INSULT_ODDS = 2
SHOUT_LEN = 16
SHOUT_MAX_TOKENS = 0
MAX_CHAT_HISTORY = 10

shout_tokens = 0
curl_stdout = ""
curl_stderr = ""
db = None
polls = []

def msg_cb(data, signal, signal_data):
    global shout_tokens
    info = weechat.info_get_hashtable(
        "irc_message_parse", { "message": signal_data } )
    srv, _ = signal.split(",", 2)
    mynick = weechat.info_get("irc_nick", srv)
    chn = info["channel"]
    line = info["arguments"].split(":", 1)[1]
    nick = info["nick"]
    is_ross = random.randint(1, ROSS_ODDS) == 1 and \
        (nick == "Rossthefox" or "ross" in line.lower())
    is_childlock = False # nick in ["h", "hex", "hexafluoride"]
    is_alpha = line.upper() != line.lower()
    is_shouting = is_alpha and line == line.upper() and len(line) >= SHOUT_LEN
    if is_shouting:
        unprovoked_odds = UNPROVOKED_SHOUT_ODDS
        shout_tokens = min(shout_tokens + 1, SHOUT_MAX_TOKENS)
    elif is_alpha:
        unprovoked_odds = UNPROVOKED_ODDS
    else:
        unprovoked_odds = UNPROVOKED_IMPOSSIBLE_ODDS
    pieces = line.split(" ", 1)
    tokn, rest = (pieces if len(pieces) == 2 else (line, ""))
    update_seen(srv, chn, nick)
    do_tell(srv, chn, nick)
    do_poll(srv, chn, nick, line)
    url = extract_url(line)
    if is_childlock:
        return weechat.WEECHAT_RC_OK
    elif url:
        run_url(srv, chn, url)
    elif tokn == "?im":
        run_im(srv, chn, rest)
    elif tokn == "?g":
        run_g(srv, chn, rest)
    elif tokn == "?gr":
        run_g(srv, chn, rest, shuf=True)
    elif tokn == "?gif":
        run_gif(srv, chn, rest)
    elif tokn == "?ir":
        run_im(srv, chn, rest, shuf=True)
    elif tokn == "?yt":
        run_yt(srv, chn, rest)
    elif tokn == "?tw":
        run_tw(srv, chn, rest)
    elif tokn == "?twr":
        run_twr(srv, chn, rest)
    elif tokn == "?tr":
        run_tw(srv, chn, rest, shuf=True)
    elif tokn == "?tu":
        run_im(srv, chn, rest, pre_q="site:tumblr.com ")
    elif tokn == "?alert":
        run_alert(srv, chn, nick);
    elif tokn == "?write":
        run_write(srv, chn, rest);
    elif tokn == "?rl":
        run_rl(srv, chn)
    elif tokn == "?ly":
        run_ly(srv, chn, rest)
    elif tokn == "?freep":
        run_freep(srv, chn, rest)
    elif tokn == "?pol":
        run_pol(srv, chn, rest)
    elif tokn == "?co":
        run_co(srv, chn, rest)
    elif tokn == "?cb":
        run_chaturbate(srv, chn, rest)
    elif tokn == "?meme":
        run_memegen(srv, chn, rest)
    elif tokn == "?ys" or \
        random.randint(1, unprovoked_odds) == 1 or \
        is_ross or \
        is_shouting:
        if tokn == "?ys":
            ys_term = rest
        elif is_ross:
            ys_term = "what is a furry"
        else:
            ys_phrases = textblob.TextBlob(line).noun_phrases
            ys_term = ys_phrases[0] if len(ys_phrases) > 0 else get_sexy_topic()
        run_ys(srv, chn, ys_term)
    elif tokn == "?ud":
        run_ud(srv, chn, rest)
    elif tokn == "?op":
        run_op(srv, chn, nick, rest)
    elif tokn == "?ti":
        run_ti(srv, chn, rest)
    elif tokn == "?dong":
        run_dong(srv, chn, rest)
    elif tokn == "?nigga":
        run_ti(srv, chn, "nigga")
    elif tokn == "?nyc":
        run_tgeo(srv, chn, "lat:[40.444269 TO 40.891423] AND lon:[-74.183121 TO -73.749847]")
    elif tokn == "?denver":
        run_tgeo(srv, chn, "lat:[39.709489 TO 39.763876] AND lon:[-105.032387 TO -104.949989]")
    elif tokn == "?leave_us_at_once":
        run_leave(srv, chn, nick, rest)
    elif tokn == "?seen":
        run_seen(srv, chn, nick, rest)
    elif tokn == "?tell":
        run_tell(srv, chn, nick, rest)
    elif tokn == "?poll":
        run_poll(srv, chn, nick, rest)
    elif mynick.lower() in line.lower() and \
        random.randint(1, PROVOKED_ODDS) == 1:
        run_insult(srv, chn) if random.randint(1, INSULT_ODDS) == 1 \
            else run_compliment(srv, chn)
    return weechat.WEECHAT_RC_OK

def run_poll(srv, chn, nick, rest):
    global polls
    m = re.search('(.+)\s+<([^>]+)>\s+(\d+)', rest)
    if not m:
        say(srv, chn, "E.g.: ?poll question <answer1,answer2,etc> 600")
        return
    question = m.group(1)
    answers = list(set([ x.strip() for x in m.group(2).split(",") ]))
    ttl = max(min(int(m.group(3)), 3600), 10)
    expire = time.time() + ttl
    polls.append({
        'srv': srv,
        'chn': chn,
        'q': question,
        'as': answers,
        'r': {},
        'exp': expire,
        'dead': False
    })
    say(srv, chn, "Tracking for %d secs..." % ttl)

def do_poll(srv, chn, nick, line):
    global polls
    now = time.time()
    for poll in polls:
        if poll['srv'] == srv and poll['chn'] == chn:
            if line in poll['as']:
                poll['r'][nick] = line
            if now >= poll['exp']:
                summarize_poll(srv, chn, poll)
                poll['dead'] = True
    polls = [ poll for poll in polls if not poll['dead'] ]

def summarize_poll(srv, chn, poll):
    rs = { a: 0 for a in poll['as'] }
    for nick in poll['r']:
        if not poll['r'][nick] in rs:
            rs[poll['r'][nick]] = 0
        rs[poll['r'][nick]] += 1
    rrs = []
    for a in rs:
        ct = rs[a]
        rrs.append("%s: %d" % (a, ct))
    rrrs = ', '.join(rrs)
    say(srv, chn, "Poll results: %s ... %s" % (poll['q'], rrrs))

def extract_url(rest):
    m = re.search('https?://\S+', rest)
    if m:
        return m.group(0)
    return None

def run_url(srv, chn, url):
    run_curl(srv, chn, url, """grep -Po '(?<=<title>).+(?=</title>)' | """ \
        """recode -f html..ascii""", "^ %s")

def run_tell(srv, chn, nick, rest):
    pieces = rest.split(" ", 1)
    if len(pieces) != 2:
        return
    to, msg = pieces
    db_write('insert into tell (srv, chn, nick, frm, msg) values (?, ?, ?, ?, ?)', srv, chn, to, nick, msg)
    say(srv, chn, "K")

def do_tell(srv, chn, nick):
    rows = db_query('select frm, msg from tell where srv = ? and chn = ? and nick = ?', srv, chn, nick)
    if len(rows) < 1:
        return
    for i in range(len(rows)):
        say(srv, chn, "%s, %s said: %s" % (nick, rows[i][0], rows[i][1]))
    db_write('delete from tell where srv = ? and chn = ? and nick = ?', srv, chn, nick)

def run_seen(srv, chn, nick, who):
    who = who.strip()
    rows = db_query('select ts from seen where srv = ? and chn = ? and nick = ?', srv, chn, who)
    if len(rows) < 1:
        if random.randint(1, 3) == 1:
            who = "John Galt"
        say(srv, chn, "Who is %s?" % (who))
    else:
        ts = datetime.datetime.fromtimestamp(int(rows[0][0])).ctime()
        say(srv, chn, "Last saw %s here on %s" % (who, ts))

def update_seen(srv, chn, nick):
    ts = int(time.time())
    db_write("insert or replace into seen (srv, chn, nick, ts) values(?, ?, ?, ?)", srv, chn, nick, ts)

def run_dong(srv, chn, rest):
    url = "http://dongerlist.com"
    run_curl(srv, chn, url, """grep -Po """ \
        """'(?<=<a class="last" href="http://dongerlist.com/page/)\d+' | """ \
        """xargs -rn1 seq 1 | shuf -n1 | xargs -rn1 -I@ curl -s """ \
        """'http://dongerlist.com/page/@' | """ \
        """grep -Po '(?<=readonly="readonly">)[^<]+(?=<)' | """ \
        """php -r 'while(($line=fgets(STDIN)) !== false) """ \
        """echo html_entity_decode($line);' | shuf -n1""", "%s")

def run_leave(srv, chn, nick, rest):
    if nick != "ceph" and nick != "Holofernes":
        msg = """"You, there," I said, glowering, for I'd no notion of his """ \
            """name. I pointed at the door. "Leave us at once. ... AT ONCE """ \
            """NIGGA." The man glanced at the king first for confirmation, """ \
            """unwise in my present humor, then finally, as I raised my """ \
            """fist to strike him, he scurried from the room..."""
        say(srv, chn, msg)
        return
    secs = 30
    if rest != "":
        try:
            secs = int(rest)
        except ValueError:
            pass
    msecs = max(1, min(600, secs)) * 1000
    say(srv, chn, "", cmd="part")
    say(srv, chn, "addreplace tmp timer " + str(msecs) + ";0;1 '' '' '/join -server " + srv + ' ' + chn, cmd="trigger")

def run_op(srv, chn, nick, rest):
    try:
        code_in = int(rest)
    except:
        return
    key = "%s|%s|%s" % (srv,chn,nick,)
    rows = db_query('select secret from auth where key = ?', key)
    if len(rows) < 1:
        return
    secret = rows[0][0]
    secret = base64.b32decode(secret.replace(' ', '').upper())
    codes = []
    leeway = 1
    tslot = int(time.time()) / 30
    for delta in range(-1 * leeway, leeway + 1):
        h = hmac.new(secret, struct.pack(">Q", tslot + delta), hashlib.sha1).digest()
        o = ord(h[19]) & 0xf
        code = (struct.unpack(">I", h[o:o+4])[0] & 0x7fffffff) % 1000000
        codes.append(code)
    if code_in in codes:
        say(srv, chn, nick, cmd="op")

def run_memegen(srv, chn, rest):
    args = [ escapeshellarg(x.strip()) for x in rest.split("|", 2) ]
    cmd = ("casperjs " + HANK_HOME + "/memegen.js " + " ".join(['%s'] * len(args)) + " | tr -d '\n'") % tuple(args)
    run_cmd(cmd, srv, chn, "%s.jpg", timeout=30000)

def run_chaturbate(srv, chn, rest):
    rest = rest.strip()
    if len(rest) > 0:
        cmd = "php %s/chaturbate.php %s" % (HANK_HOME, escapeshellarg(rest))
    else:
        cmd = "php %s/chaturbate.php" % (HANK_HOME)
    run_cmd(cmd, srv, chn, "%s")

def run_freep(srv, chn, rest):
    url = "http://www.freerepublic.com/tag/" + "*/index"
    run_curl(srv, chn, url, """grep -Po '/focus/[^/]+/\d+/posts' | """ \
        """shuf -n1 | """ \
        """xargs -I@ curl -s 'http://www.freerepublic.com/@' | """ \
        """grep -A1 '<div class="b2">' | grep -Po '(?<=<p>).+(?=</p>)' | """ \
        """shuf -n1 | recode -f html..ascii""", "%s")

def run_alert(srv, chn, from_nick):
    buffer = weechat.info_get("irc_buffer", srv + "," + chn)
    if not buffer:
        return
    nicks = []
    nicklist = weechat.infolist_get("nicklist", buffer, "")
    is_op = False
    while weechat.infolist_next(nicklist):
        nick = weechat.infolist_string(nicklist, "name")
        nick_type = weechat.infolist_string(nicklist, "type")
        nick_prefix = weechat.infolist_string(nicklist, "prefix")
        if nick_type == "nick":
            nicks.append(nick)
            if nick == from_nick and (nick_prefix == "@" or nick_prefix == "&"):
                is_op = True
    weechat.infolist_free(nicklist)
    if is_op:
        say(srv, chn, "Alert: " + (", ".join(nicks)))

def run_ud(srv, chn, rest):
    url = "http://www.urbandictionary.com/define.php?" + \
        urllib.urlencode({ "term": rest })
    run_curl(srv, chn, url, """dos2unix | """ \
        """awk -von=0 '/<\/div>/{if(on==1)exit} """ \
        """on==1{print $0} /<div class=.meaning.>/{on=1}' | """ \
        """lynx -stdin -dump | sed -e 's/^\s\+//' | paste -sd' '""", "%s")

def run_pol(srv, chn, rest):
    url = "http://boards.4chan.org/pol/"
    run_curl(srv, chn, url, """grep -Po '(?<=thread/)\d+' | uniq | """ \
        """tail -n+2 | head -n1 | """ \
        """xargs -I@ curl -s 'http://boards.4chan.org/pol/thread/@' | """ \
        """grep -Po '<blockquote[^>]+>[^<]+' | shuf -n1 | cut -d'>' -f2 | """ \
        """recode -f html..ascii""", "%s")

def run_ly(srv, chn, rest):
    url = "http://genius.com/search?" + \
        urllib.urlencode({ "q": rest })
    run_curl(srv, chn, url, """grep -Po """
        """'(?<=href=")http://genius.com/[^"]+(?=" class=" song_link")' | """ \
        """head -n1 | xargs curl -s | lynx -stdin -dump | """ \
        """tail -n+25 | """ \
        """sed -e 's/^\s\+//' | """ \
        """sed 's/\[[0-9]\+\]//' | """ \
        """ack -i -C1 """ + escapeshellarg(rest) + """ | head -n3""", "%s")

def run_co(srv, chn, rest):
    pieces = rest.split(" ", 1)
    lang, code = (pieces if len(pieces) == 2 else ("", rest))
    url = "http://codepad.org"
    run_curl(srv, chn, url, """ack --no-color -A10 '^<pre>$' | """ \
        """lynx -stdin -dump | """ \
        """awk 'BEGIN{s=1} /References/{s=0} {if (s==1)print $0}' | """ \
        """xargs echo""", "%s", \
        "lang=%s&code=%s&private=True&run=True&submit=Submit" % \
        (urllib.quote(lang), urllib.quote(code)))

def run_ys(srv, chn, q):
    url = "https://www.youtube.com/results?" + \
        urllib.urlencode({ "search_query": qq(q) })
    run_curl(srv, chn, url, """grep -Po '(?<=watch\?v=).{11}' | sort | """ \
        """uniq | shuf -n1 | xargs -n1 -I@ """ \
        """curl -s 'https://content.googleapis.com/youtube/v3/""" \
        """commentThreads?part=snippet&maxResults=100&videoId=@&textFormat=""" \
        """plainText&key=""" + YOUTUBE_API_KEY + """' | """ \
        """grep '"textDisplay"' | cut -d: -f2- | cut -c2- | sed 's/,$//' | """ \
        """egrep -iv '(\+|#|@|:|vid|record|upload|stream|youtube|thank| """ \
        """watch|download)' | """ \
        """shuf -n1 | json_decode -p | paste -sd' ' | """ \
        """recode -f html..ascii""", "%s")

def run_insult(srv, chn):
    url = "http://www.insultgenerator.org"
    run_curl(srv, chn, url, """grep -Po '(?<=^<br><br>).*?(?=</div>$)' | """ \
        """recode -f html..ascii""", "%s")

def run_compliment(srv, chn):
    url = "http://www.madsci.org/cgi-bin/cgiwrap/~lynn/jardin/SCG"
    run_curl(srv, chn, url, """tr '\n' ' ' | """ \
        """grep -Po '(?<=<h2>).*?(?=</h2>)' | """ \
        """sed 's/^[ \t]*//;s/[ \t]*$//' | recode -f html..ascii""", "%s")

def run_im(srv, chn, q, pre_q="", shuf=False):
    url = "https://www.google.com/search?" + \
        urllib.urlencode({
            "site": "",
            "tbm": "isch",
            "source": "hp",
            "q": pre_q + qq(q)
        })
    shuf_or_head = "shuf" if shuf else "head"
    run_curl(srv, chn, url, """grep -Po '(?<="ou":)".+?"' | """ + \
        """grep -v photobucket | """ + \
        shuf_or_head + """ -n1 | """ \
        """php -r 'echo @json_decode(file_get_contents("php://stdin"));'""",
        "Found " + qq(q) + ": %s")

def run_g(srv, chn, q, shuf=False):
    url = "https://www.google.com/search?" + \
        urllib.urlencode({
            "site": "",
            "source": "hp",
            "q": qq(q)
        })
    shuf_or_head = "shuf" if shuf else "head"
    run_curl(srv, chn, url, """lynx -stdin -dump | """ \
        """grep -Po '\d+\.\s+https?://\S+' | """ \
        """grep -Po 'https?://\S+' | """ \
        """grep -Pv '(google|w3.org|schema.org)' | """ + \
        shuf_or_head + """ -n1 | """ \
        """php -r "echo urldecode(urldecode(fgets(STDIN)));" | """ \
        """tr ' ' '+'""", "Found " + qq(q) + ": %s")

def run_gif(srv, chn, q):
    url = "https://www.google.com/search?" + \
        urllib.urlencode({
            "tbm": "isch",
            "tbs": "itp:animated",
            "q": qq(q)
        })
    shuf_or_head = "shuf"
    run_curl(srv, chn, url, """grep -Po '(?<="ou":").+?(?=")' | """ + \
        shuf_or_head + """ -n1 | """ \
        """php -r "echo urldecode(urldecode(fgets(STDIN)));" | """ \
        """tr ' ' '+'""", "Found " + qq(q) + ": %s")

def run_write(srv, chn, q):
    url = "http://www.cs.toronto.edu/~graves/handwriting.cgi?" + \
        urllib.urlencode({
            "text": q,
            "style": "",
            "bias": "0.15",
            "samples": "1"
        })
    run_curl(srv, chn, url,
        """grep -Po '(?<=data:image/jpeg;base64,)[^"]+' | base64 -d | """ \
        """curl -s --compressed -XPOST -F 'image=@-' """ \
        """-H 'Authorization: Client-ID """ + IMGUR_CLIENT_ID + """' """ \
        """'https://api.imgur.com/3/image' | grep -Po '(?<="id":")[^"]+' | """ \
        """xargs -rn1 printf 'http://i.imgur.com/%s.png'""", "%s :)")

def run_yt(srv, chn, q):
    url = "https://www.youtube.com/results?" + \
        urllib.urlencode({
            "search_query": qq(q)
        })
    run_curl(srv, chn, url, """grep -Po '(?<=watch\?v=)[^"&<]+' | """ \
        """head -n1""", "Found " + qq(q) + ": http://youtu.be/%s")

def run_tw(srv, chn, q, shuf=False):
    url = "https://twitter.com/search?" + \
        urllib.urlencode({
            "f": "realtime",
            "q": qq(q)
        })
    shuf_or_head = "shuf" if shuf else "head"
    run_curl(srv, chn, url, \
        """grep -Po '(?<=data-aria-label-part="0">).*?(?=</p>)' | """ \
        """sed -e 's/<[^>]*>//g' | grep -Pv '^\s*$' | """ \
        """recode -f html..ascii | """ + shuf_or_head + """ -n1""", "%s")

def run_twr(srv, chn, q, shuf=False):
    url = "https://twitter.com/search?" + \
        urllib.urlencode({
            "f": "realtime",
            "q": qq(q)
        })
    shuf_or_head = "shuf" if shuf else "head"
    run_curl(srv, chn, url, \
        """grep -Po '(?<=data-aria-label-part="0">).*?(?=</p>)' | """ \
        """sed -e 's/<[^>]*>//g' | grep -Pv '^\s*$' | """ \
        """recode -f html..ascii | """ + shuf_or_head + """ -n1 | """ \
        """php -r "echo urlencode(fgets(STDIN));" | """ \
        """xargs -rn1 printf 'http://www.cs.toronto.edu/~graves/""" \
        """handwriting.cgi?style=&bias=0.15&samples=1&text=%s' | """ \
        """xargs -rn1 curl -s | """ \
        """grep -Po '(?<=data:image/jpeg;base64,)[^"]+' | base64 -d | """ \
        """curl -s --compressed -XPOST -F 'image=@-' """ \
        """-H 'Authorization: Client-ID """ + IMGUR_CLIENT_ID + """' """ \
        """'https://api.imgur.com/3/image' | grep -Po '(?<="id":")[^"]+' | """ \
        """xargs -rn1 printf 'http://i.imgur.com/%s.png'""", "%s :0")

def run_ti(srv, chn, q):
    url = "https://twitter.com/search?" + \
        urllib.urlencode({
            "f": "images",
            "vertical": "default",
            "q": qq(q)
        })
    run_curl(srv, chn, url, \
        """grep -Po '(?<=data-resolved-url-large=").*?(?=")' | """ \
        """recode -f html..ascii | shuf -n1""", "%s")

def run_tgeo(srv, chn, q):
    url = "http://onemilliontweetmap.com/omtm/search?" + \
        urllib.urlencode({
            "from": "0",
            "q": qq(q),
            "size": "50"
        })
    run_curl(srv, chn, url, \
        """grep -Po '(?<="text":").*?(?=")' | """ \
        """recode -f html..ascii | shuf -n1""", "%s")

def run_rl(srv, chn):
    logfile = '~/.weechat/logs/irc.%s.%s.weechatlog' % (srv, chn)
    cmd = '''tail -c "+$[ 1 + $[ RANDOM % $(stat -c '%s' ''' + \
        logfile + \
        ''') ]]" ''' + \
        logfile + \
        '''| head -n21 | tail -n20 2>/dev/null | ''' \
        '''grep -Pv '(-->|<--|You are now known as)' | shuf -n1 | cut -f3-'''
    weechat.hook_process(
        "bash -c %s" % (escapeshellarg(cmd)),
        5000,
        "run_proc_cb",
        json.dumps({'srv': srv, 'chn': chn, 'fmt': "%s"}))

def run_curl(srv, chn, url, piping, fmt, data=False, curlopts="-s -L", \
    with_err=False):
    cmd = ("curl " + curlopts + " -A %s %s %s %s | %s") % \
        (escapeshellarg(USER_AGENT), \
        ("-d %s" % escapeshellarg(data)) if data else "", \
        escapeshellarg(url), \
        "2>&1" if with_err else "",
        piping)
    run_cmd(cmd, srv, chn, fmt)

def run_cmd(cmd, srv, chn, fmt, timeout=5000):
    weechat.hook_process(
        "bash -c %s" % (escapeshellarg(cmd)),
        timeout,
        "run_proc_cb",
        json.dumps({'srv': srv, 'chn': chn, 'fmt': fmt}))

def qq(s):
    return s

def say(srv, chn, msg, cmd="say"):
    global shout_tokens
    buffer = weechat.info_get("irc_buffer", srv + "," + chn)
    if not buffer:
        return
    if shout_tokens > 0 and not 'http' in msg:
        shout_tokens -= 1
        msg = msg.upper()
    if len(msg) > 512:
        msg = msg[:512] + "... aight ENOUGH"
    weechat.command(buffer, "/" + cmd + " " + msg)

def db_exec(sql, *args):
    global db
    # weechat.prnt("", "db_exec: sql=%s args=%s" % (sql, args, ))
    if not db:
        db = sqlite3.connect(os.path.expanduser(SQLITE_DB), isolation_level=None)
    cursor = db.cursor()
    cursor.execute(sql, args)
    return cursor

def db_query(sql, *args):
    try:
        cur = db_exec(sql, *args)
        retval = cur.fetchall()
        cur.close()
    except Exception as e:
        weechat.prnt("", "db_query: %s" % (str(e),))
        return []
    return retval

def db_write(sql, *args):
    try:
        cur = db_exec(sql, *args)
        retval = cur.rowcount
        cur.close()
    except Exception as e:
        weechat.prnt("", "db_write: %s" % (str(e),))
        return 0
    return retval

def escapeshellarg(arg):
    return "\\'".join("'" + p + "'" for p in arg.split("'"))

def get_sexy_topic():
    return random.choice([
        'anal sex',
        'butt bang',
        'cunnilingus',
        'dick dong',
        'erotica taboo',
        'fellatio how to',
        'gender bending',
        'hormone treatment',
        'intercourse how to',
        'jizz how to',
        'kinky how to',
        'libido how to',
        'mating humans',
        'nipple tweaking',
        'oral sex how to',
        'perverted sex',
        'queer sex',
        'reproductive organs',
        'sex how to have',
        'transsexual tits',
        'unison orgasm',
        'virgin how to',
        'whoredom'
        'xxx sex',
        'youngster sex',
        'zebra sex'])

def run_proc_cb(udata, command, rc, stdout, stderr):
    global curl_stdout, curl_stderr
    curl_stdout += stdout
    curl_stderr += stderr
    rci = int(rc)
    udata = json.loads(udata)
    fmt = udata['fmt']
    if rci >= 0:
        weechat.prnt("", "hankbot: rc=%d command=%s stderr=%s stdout=%s" % \
            (rci, command, curl_stderr, curl_stdout))
        if rci == 0:
            # curl_stdout = curl_stdout.strip()
            # curl_stdout = ''.join([i if ord(i) < 128 else '?' for i in curl_stdout])
            if curl_stdout != "":
                say(udata['srv'], udata['chn'], fmt % (curl_stdout))
        else:
            say(udata['srv'], udata['chn'], ':(')
        curl_stdout = ""
        curl_stderr = ""
    return weechat.WEECHAT_RC_OK

weechat.hook_signal("*,irc_in2_privmsg", "msg_cb", "");
