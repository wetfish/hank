import base64
import collections
import hashlib
import hmac
import json
import os
import random
import sqlite3
import struct
import textblob
import time
import urllib
import weechat

weechat.register("hankbot", "ceph", "2.4.3", "GPL3", "hankbot", "", "")

YOUTUBE_API_KEY = "AIzaSyAiYfOvXjvhwUFZ1VPn696guJcd2TJ-Lek"
SQLITE_DB = "~/hank.db"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, " \
    "like Gecko) Chrome/47.0.2526.106 Safari/537.36"
UNPROVOKED_ODDS = 75
UNPROVOKED_SHOUT_ODDS = 20
ROSS_ODDS = 5
PROVOKED_ODDS = 5
INSULT_ODDS = 2
SHOUT_LEN = 16
SHOUT_MAX_TOKENS = 1
MAX_CHAT_HISTORY = 10

shout_tokens = 0
chat_history = {}
curl_stdout = ""
curl_stderr = ""
db = None

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
    is_shouting = len(line) >= SHOUT_LEN and \
        line == line.upper()
    unprovoked_odds = UNPROVOKED_ODDS
    if is_shouting:
        unprovoked_odds = UNPROVOKED_SHOUT_ODDS
        shout_tokens = min(shout_tokens + 1, SHOUT_MAX_TOKENS)
    pieces = line.split(" ", 1)
    tokn, rest = (pieces if len(pieces) == 2 else (line, ""))
    if tokn == "?im":
        run_im(srv, chn, rest)
    elif tokn == "?comic":
        run_comic(srv, chn, nick, rest)
    elif tokn == "?gif":
        run_gif(srv, chn, rest)
    elif tokn == "?ir":
        run_im(srv, chn, rest, shuf=True)
    elif tokn == "?yt":
        run_yt(srv, chn, rest)
    elif tokn == "?tw":
        run_tw(srv, chn, rest)
    elif tokn == "?tr":
        run_tw(srv, chn, rest, shuf=True)
    elif tokn == "?tu":
        run_im(srv, chn, rest, pre_q="site:tumblr.com ")
    elif tokn == "?alert":
        run_alert(srv, chn, nick);
    elif tokn == "?rl":
        run_rl(srv, chn)
    elif tokn == "?ly":
        run_ly(srv, chn, rest)
    elif tokn == "?freep":
        run_freep(srv, chn, rest)
    elif tokn == "?pol":
        run_pol(srv, chn, rest)
    elif tokn == "?c":
        run_co(srv, chn, "C", rest)
    elif tokn == "?cpp":
        run_co(srv, chn, "C++", rest)
    elif tokn == "?d":
        run_co(srv, chn, "D", rest)
    elif tokn == "?haskell":
        run_co(srv, chn, "Haskell", rest)
    elif tokn == "?lua":
        run_co(srv, chn, "Lua", rest)
    elif tokn == "?ocaml":
        run_co(srv, chn, "OCaml", rest)
    elif tokn == "?php":
        run_co(srv, chn, "PHP", rest)
    elif tokn == "?pl":
        run_co(srv, chn, "Perl", rest)
    elif tokn == "?py":
        run_co(srv, chn, "Python", rest)
    elif tokn == "?rb":
        run_co(srv, chn, "Ruby", rest)
    elif tokn == "?scheme":
        run_co(srv, chn, "Scheme", rest)
    elif tokn == "?tcl":
        run_co(srv, chn, "Tcl", rest)
    elif tokn == "?cb":
        run_chaturbate(srv, chn, rest)
    elif tokn == "?ys" or \
        random.randint(1, UNPROVOKED_ODDS) == 1 or \
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
    elif tokn == "?op":
        run_op(srv, chn, nick, rest)
    elif mynick.lower() in line.lower() and \
        random.randint(1, PROVOKED_ODDS) == 1:
        run_insult(srv, chn) if random.randint(1, INSULT_ODDS) == 1 \
            else run_compliment(srv, chn)
    return weechat.WEECHAT_RC_OK

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

def run_chaturbate(srv, chn, rest):
    rest = rest.strip()
    if len(rest) > 0:
        cmd = "chaturbate.php %s" % escapeshellarg(rest)
    else:
        cmd = "chaturbate.php"
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

def run_co(srv, chn, lang, code):
    url = "http://codepad.org"
    run_curl(srv, chn, url, """ack --no-color -A10 '^<pre>$' | """ \
        """lynx -stdin -dump | """ \
        """awk 'BEGIN{s=1} /References/{s=0} {if (s==1)print $0}' | """ \
        """xargs echo""", "%s", \
        "lang=%s&code=%s&private=True&run=True&submit=Submit" % \
        (urllib.quote(lang), urllib.quote(code)))

def run_ys(srv, chn, q):
    url = "https://www.youtube.com/results?" + \
        urllib.urlencode({ "search_query": q })
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
            "q": pre_q + q
        })
    shuf_or_head = "shuf" if shuf else "head"
    run_curl(srv, chn, url, """grep -Po '(?<="ou":").+?(?=")' | """ + \
        shuf_or_head + """ -n1 | """ \
        """php -r "echo urldecode(urldecode(fgets(STDIN)));" | """ \
        """tr ' ' '+'""", "Found " + q + ": %s")

def run_gif(srv, chn, q):
    url = "https://www.google.com/search?" + \
        urllib.urlencode({
            "tbm": "isch",
            "tbs": "itp:animated",
            "q": q
        })
    shuf_or_head = "shuf"
    run_curl(srv, chn, url, """grep -Po '(?<="ou":").+?(?=")' | """ + \
        shuf_or_head + """ -n1 | """ \
        """php -r "echo urldecode(urldecode(fgets(STDIN)));" | """ \
        """tr ' ' '+'""", "Found " + q + ": %s")

def run_yt(srv, chn, q):
    url = "https://www.youtube.com/results?" + \
        urllib.urlencode({
            "search_query": q
        })
    run_curl(srv, chn, url, """grep -Po '(?<=watch\?v=)[^"&<]+' | """ \
        """head -n1""", "Found " + q + ": http://youtu.be/%s")

def run_tw(srv, chn, q, shuf=False):
    url = "https://twitter.com/search?" + \
        urllib.urlencode({
            "f": "realtime",
            "q": q
        })
    shuf_or_head = "shuf" if shuf else "head"
    run_curl(srv, chn, url, \
        """grep -Po '(?<=data-aria-label-part="0">).*?(?=</p>)' | """ \
        """sed -e 's/<[^>]*>//g' | grep -Pv '^\s*$' | """ \
        """recode -f html..ascii | """ + shuf_or_head + """ -n1""", "%s")

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

def run_cmd(cmd, srv, chn, fmt):
    weechat.hook_process(
        "bash -c %s" % (escapeshellarg(cmd)),
        5000,
        "run_proc_cb",
        json.dumps({'srv': srv, 'chn': chn, 'fmt': fmt}))

def say(srv, chn, msg, cmd="say"):
    global shout_tokens
    buffer = weechat.info_get("irc_buffer", srv + "," + chn)
    if not buffer:
        return
    if shout_tokens > 0 and not 'http' in msg:
        shout_tokens -= 1
        msg = msg.upper()
    if len(msg) > 350:
        msg = msg[:350] + "... aight ENOUGH"
    weechat.command(buffer, "/" + cmd + " " + msg)

def db_exec(sql, *args):
    global db
    weechat.prnt("", "db_exec: sql=%s args=%s" % (sql, args, ))
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
            curl_stdout = curl_stdout.strip()
            curl_stdout = ''.join([i if ord(i) < 128 else '?' for i in curl_stdout])
            if curl_stdout != "":
                say(udata['srv'], udata['chn'], fmt % (curl_stdout))
        else:
            say(udata['srv'], udata['chn'], ':(')
        curl_stdout = ""
        curl_stderr = ""
    return weechat.WEECHAT_RC_OK

weechat.hook_signal("*,irc_in2_privmsg", "msg_cb", "");
