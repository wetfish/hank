import weechat
import random
import urllib
import json
import time
import textblob
import sqlite3
import os

weechat.register("hankbot", "ceph", "2.2.1", "GPL3", "hankbot", "", "")

SQLITE_DB = "~/hank.db"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, " \
    "like Gecko) Chrome/39.0.2171.95 Safari/537.36"
UNPROVOKED_ODDS = 50
ROSS_ODDS = 5
PROVOKED_ODDS = 5
INSULT_ODDS = 2

last_unprovoked_time = 0
def msg_cb(data, signal, signal_data):
    global UNPROVOKED_ODDS
    global PROVOKED_ODDS
    global INSULT_ODDS
    info = weechat.info_get_hashtable(
        "irc_message_parse", { "message": signal_data } )
    srv, _ = signal.split(",", 2)
    mynick = weechat.info_get("irc_nick", srv)
    chn = info["channel"]
    line = info["arguments"].split(":", 1)[1]
    nick = info["nick"]
    pieces = line.split(" ", 1)
    is_ross = random.randint(1, ROSS_ODDS) == 1 and \
        (info["nick"] == "Rossthefox" or "ross" in line.lower())
    tokn, rest = (pieces if len(pieces) == 2 else (line, ""))
    if tokn == "?im":
        run_im(srv, chn, rest)
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
    elif tokn == "?weather":
        run_weather(srv, chn, rest)
    elif tokn == "?rl":
        run_rl(srv, chn)
    elif tokn == "?ly":
        run_ly(srv, chn, rest)
    elif tokn == "?freep":
        run_freep(srv, chn, rest)
    elif tokn == "?seen":
        run_seen(srv, chn, rest)
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
    elif tokn == "?ys" or random.randint(1, UNPROVOKED_ODDS) == 1 or is_ross:
        if tokn == "?ys":
            ys_term = rest
        elif is_ross:
            ys_term = "what is a furry"
        else:
            ys_phrases = textblob.TextBlob(line).noun_phrases
            ys_term = ys_phrases[0] if len(ys_phrases) > 0 else get_sexy_topic()
        run_ys(srv, chn, ys_term)
    elif tokn == "?learn":
        run_learn(srv, chn, nick, rest)
    elif tokn == "?unlearn":
        run_unlearn(srv, chn, rest)
    elif tokn[:1] == '?':
        val = get_learned(srv, chn, tokn[1:])
        if val:
            say(srv, chn, val)
    elif mynick.lower() in line.lower() and \
        random.randint(1, PROVOKED_ODDS) == 1:
        run_insult(srv, chn) if random.randint(1, INSULT_ODDS) == 1 \
            else run_compliment(srv, chn)
    return weechat.WEECHAT_RC_OK

def run_seen(srv, chn, rest):
    global NOUN_LIST
    url = "https://www.google.com/search?" + \
        urllib.urlencode({
            "q": '"taking a * on a *" OR "taking a * in a *"' \
                ' OR "doing a * in a *" OR "doing a * on a *"',
            "start": random.randint(0, 900)
        })
    rest = rest.strip()
    hash_1 = hash(rest + str(time.localtime().tm_yday))
    hash_2 = hash(str(time.localtime().tm_yday) + rest)
    time_ago = str(hash_1 % 11) + " centuries"
    noun1 = NOUN_LIST[hash_1 % len(NOUN_LIST)]
    noun2 = NOUN_LIST[hash_2 % len(NOUN_LIST)]
    msg = "Last saw " + rest + " " + time_ago + " ago taking a shit on a " + \
        noun1 + " with a " + noun2
    say(srv, chn, msg)

def run_freep(srv, chn, rest):
    url = "http://www.freerepublic.com/tag/" + "*/index"
    run_curl(srv, chn, url, """grep -Po '/focus/[^/]+/\d+/posts' | """ \
        """shuf -n1 | """ \
        """xargs -I@ curl -s 'http://www.freerepublic.com/@' | """ \
        """grep -A1 '<div class="b2">' | grep -Po '(?<=<p>).+(?=</p>)' | """ \
        """shuf -n1 | recode -f html..ascii""", "%s")

def run_weather(srv, chn, rest):
    url = "http://www.wunderground.com/cgi-bin/findweather/getForecast?" + \
        urllib.urlencode({ "query": rest })
    run_curl(srv, chn, url, """grep -Po 'zmw:\d+[^"]+' | """ \
        """xargs -n1 -I@ curl -s 'http://api.wunderground.com/api/""" \
        """c991975b7f4186c0/forecast/q/@.json' | """ \
        """json_decode -px 'forecast.txt_forecast.forecastday.0.fcttext' | """ \
        """recode -f html..ascii""", "%s")

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
        """ack -A1000 'Copy Embed' | tail -n+3 | """ \
        """awk '/^\w/{s=1} {if (s==0) print $0}' | """ \
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
        """uniq | shuf -n1 | """ \
        """xargs -n1 -I@ """ \
        """curl -s "https://www.youtube.com/all_comments?v=@" | """ \
        """grep -Po '(?<=comment-text-content">).+?(?=</div>)' | """ \
        """sed -e 's|<[^>]*>||g' | """ \
        """egrep -iv '(\+|#|@|:|vid|record|upload|stream|youtube|""" \
        """thank|post)' | awk 'length<=380' | """ \
        """shuf -n1 | recode -f html..ascii""", "%s")

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
    run_curl(srv, chn, url, """grep -Po '(?<=imgurl=).+?(?=&amp;)' | """ + \
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
    global USER_AGENT
    cmd = ("curl " + curlopts + " -A %s %s %s %s | %s") % \
        (escapeshellarg(USER_AGENT), \
        ("-d %s" % escapeshellarg(data)) if data else "", \
        escapeshellarg(url), \
        "2>&1" if with_err else "",
        piping)
    weechat.hook_process(
        "bash -c %s" % (escapeshellarg(cmd)),
        5000,
        "run_proc_cb",
        json.dumps({'srv': srv, 'chn': chn, 'fmt': fmt}))

def run_learn(srv, chn, author, rest):
    now = int(time.time())
    parts = rest.split(' ', 2)
    rowc = 0
    if len(parts) == 2 and \
        len(parts[0].strip()) > 0 and \
        len(parts[1].strip()) > 0:
        rowc = db_write('insert into learn(key, val, author, created) ' \
            'values(?,?,?,?)', parts[0].strip(), parts[1].strip(), author, now)
    say(srv, chn, 'K' if rowc > 0 else ':|')

def run_unlearn(srv, chn, rest):
    now = int(time.time())
    rowc = db_write('delete from learn where key = ?', rest)
    say(srv, chn, ('Forgot %d thing(s).' % (rowc)) if rowc > 0 else ':|')

def get_learned(srv, chn, tokn):
    rows = db_query('select val from learn where key = ? ' \
        'order by random() limit 1', tokn)
    if len(rows) > 0:
        return rows[0][0]
    return None

def say(srv, chn, msg):
    buffer = weechat.info_get("irc_buffer", srv + "," + chn)
    if buffer:
        weechat.command(buffer, "/say " + msg)

db = None
def db_exec(sql, *args):
    global db
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
    except:
        return []
    return retval

def db_write(sql, *args):
    try:
        cur = db_exec(sql, *args)
        retval = cur.rowcount
        cur.close()
    except:
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

curl_stdout = ""
curl_stderr = ""
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

NOUN_LIST = [
   "achiever",
   "acoustics",
   "act",
   "activity",
   "actor",
   "addition",
   "adjustment",
   "advertisement",
   "advice",
   "aftermath",
   "afternoon",
   "afterthought",
   "agreement",
   "air",
   "airport",
   "alarm",
   "alley",
   "amount",
   "amusement",
   "anger",
   "angle",
   "animal",
   "answer",
   "ant",
   "apparatus",
   "apparel",
   "apple",
   "appliance",
   "approval",
   "arch",
   "argument",
   "arithmetic",
   "arm",
   "art",
   "attack",
   "attempt",
   "attention",
   "attraction",
   "aunt",
   "authority",
   "babies",
   "baby",
   "back",
   "badge",
   "bag",
   "bait",
   "balance",
   "ball",
   "balls",
   "banana",
   "band",
   "base",
   "basin",
   "basket",
   "bat",
   "battle",
   "bead",
   "beam",
   "bean",
   "bear",
   "beast",
   "bed",
   "beds",
   "bee",
   "beetle",
   "beggar",
   "beginner",
   "behavior",
   "belief",
   "believe",
   "bell",
   "berry",
   "bike",
   "bird",
   "birth",
   "bit",
   "blade",
   "blood",
   "blow",
   "board",
   "boat",
   "body",
   "bomb",
   "bone",
   "book",
   "boot",
   "border",
   "bottle",
   "boundary",
   "box",
   "boy",
   "brain",
   "brake",
   "branch",
   "brass",
   "bread",
   "breakfast",
   "breath",
   "brick",
   "bridge",
   "brother",
   "brush",
   "bubble",
   "bucket",
   "building",
   "bulb",
   "bun",
   "burn",
   "burst",
   "bushes",
   "business",
   "butter",
   "button",
   "cabbage",
   "cable",
   "cactus",
   "cake",
   "calculator",
   "calendar",
   "camera",
   "camp",
   "can",
   "canvas",
   "cap",
   "car",
   "care",
   "carpenter",
   "carriage",
   "cars",
   "cart",
   "cast",
   "cat",
   "cattle",
   "cause",
   "cave",
   "celery",
   "cellar",
   "cemetery",
   "cent",
   "chain",
   "chair",
   "chalk",
   "chance",
   "change",
   "channel",
   "cheese",
   "cherries",
   "cherry",
   "chess",
   "chicken",
   "children",
   "chin",
   "church",
   "circle",
   "clam",
   "class",
   "clock",
   "cloth",
   "cloud",
   "clover",
   "club",
   "coach",
   "coal",
   "coast",
   "coat",
   "cobweb",
   "coil",
   "collar",
   "color",
   "comb",
   "comfort",
   "committee",
   "company",
   "comparison",
   "competition",
   "condition",
   "connection",
   "control",
   "cook",
   "copper",
   "copy",
   "cord",
   "cork",
   "corn",
   "cough",
   "country",
   "cover",
   "cow",
   "crack",
   "crate",
   "crayon",
   "cream",
   "creator",
   "creature",
   "credit",
   "crib",
   "crime",
   "crook",
   "crow",
   "crown",
   "crush",
   "cry",
   "cub",
   "cup",
   "current",
   "curtain",
   "curve",
   "cushion",
   "dad",
   "daughter",
   "day",
   "death",
   "debt",
   "decision",
   "deer",
   "degree",
   "design",
   "desire",
   "desk",
   "destruction",
   "detail",
   "development",
   "digestion",
   "dime",
   "dinner",
   "dinosaurs",
   "direction",
   "dirt",
   "discovery",
   "discussion",
   "disease",
   "disgust",
   "distance",
   "distribution",
   "division",
   "dock",
   "doctor",
   "dog",
   "doll",
   "donkey",
   "door",
   "downtown",
   "drain",
   "drawer",
   "dress",
   "drink",
   "driving",
   "drop",
   "drug",
   "drum",
   "duck",
   "dust",
   "ear",
   "edge",
   "education",
   "effect",
   "egg",
   "eggs",
   "elbow",
   "end",
   "engine",
   "error",
   "event",
   "example",
   "exchange",
   "existence",
   "expansion",
   "experience",
   "expert",
   "eye",
   "face",
   "fact",
   "fairies",
   "fall",
   "family",
   "fan",
   "farm",
   "father",
   "faucet",
   "fear",
   "feast",
   "feather",
   "feeling",
   "feet",
   "fiction",
   "field",
   "fifth",
   "fight",
   "finger",
   "fire",
   "fish",
   "flag",
   "flame",
   "flavor",
   "flesh",
   "flight",
   "flock",
   "floor",
   "flower",
   "fly",
   "fog",
   "fold",
   "food",
   "foot",
   "force",
   "fork",
   "form",
   "fowl",
   "frame",
   "friction",
   "friend",
   "frog",
   "front",
   "fruit",
   "fuel",
   "furniture",
   "game",
   "garden",
   "gate",
   "geese",
   "ghost",
   "giants",
   "giraffe",
   "girl",
   "glass",
   "glove",
   "glue",
   "goat",
   "gold",
   "good-bye",
   "goose",
   "government",
   "governor",
   "grade",
   "grain",
   "grandfather",
   "grandmother",
   "grape",
   "grass",
   "grip",
   "ground",
   "group",
   "growth",
   "guide",
   "guitar",
   "gun",
   "hair",
   "hall",
   "hammer",
   "hand",
   "harbor",
   "harmony",
   "hat",
   "head",
   "health",
   "hearing",
   "heart",
   "heat",
   "help",
   "hen",
   "hill",
   "history",
   "hobbies",
   "hole",
   "holiday",
   "home",
   "honey",
   "hook",
   "hope",
   "horn",
   "horse",
   "hose",
   "hospital",
   "hot",
   "hour",
   "house",
   "humor",
   "hydrant",
   "ice",
   "icicle",
   "idea",
   "impulse",
   "income",
   "increase",
   "industry",
   "ink",
   "insect",
   "instrument",
   "insurance",
   "interest",
   "invention",
   "iron",
   "island",
   "jail",
   "jam",
   "jar",
   "jeans",
   "jelly",
   "jewel",
   "join",
   "joke",
   "journey",
   "judge",
   "juice",
   "jump",
   "kettle",
   "key",
   "kick",
   "kiss",
   "kite",
   "kitten",
   "kitty",
   "knee",
   "knife",
   "knot",
   "knowledge",
   "laborer",
   "lace",
   "ladybug",
   "lake",
   "lamp",
   "land",
   "language",
   "laugh",
   "lawyer",
   "lead",
   "leaf",
   "learning",
   "leather",
   "leg",
   "letter",
   "lettuce",
   "level",
   "library",
   "lift",
   "light",
   "limit",
   "line",
   "lip",
   "liquid",
   "list",
   "lizards",
   "loaf",
   "lock",
   "look",
   "loss",
   "love",
   "low",
   "lumber",
   "lunch",
   "machine",
   "magic",
   "maid",
   "mailbox",
   "man",
   "map",
   "marble",
   "mark",
   "mask",
   "mass",
   "match",
   "meal",
   "measure",
   "meat",
   "meeting",
   "memory",
   "men",
   "metal",
   "mice",
   "middle",
   "milk",
   "mind",
   "mine",
   "minister",
   "mint",
   "minute",
   "mist",
   "mitten",
   "mom",
   "money",
   "monkey",
   "month",
   "moon",
   "morning",
   "mother",
   "motion",
   "mountain",
   "mouth",
   "move",
   "muscle",
   "music",
   "nail",
   "name",
   "nation",
   "neck",
   "need",
   "nerve",
   "nest",
   "net",
   "news",
   "night",
   "noise",
   "north",
   "nose",
   "note",
   "number",
   "nut",
   "oatmeal",
   "observation",
   "ocean",
   "offer",
   "office",
   "oil",
   "operation",
   "opinion",
   "orange",
   "order",
   "organization",
   "ornament",
   "oven",
   "owl",
   "owner",
   "page",
   "pail",
   "pain",
   "pan",
   "paper",
   "parcel",
   "parent",
   "park",
   "part",
   "party",
   "passenger",
   "paste",
   "patch",
   "payment",
   "peace",
   "pear",
   "pen",
   "person",
   "pest",
   "pet",
   "pickle",
   "picture",
   "pie",
   "pig",
   "pin",
   "pipe",
   "pizzas",
   "place",
   "plane",
   "plant",
   "plants",
   "plastic",
   "plate",
   "play",
   "pleasure",
   "plot",
   "plough",
   "pocket",
   "point",
   "poison",
   "police",
   "polish",
   "pollution",
   "popcorn",
   "porter",
   "position",
   "pot",
   "powder",
   "power",
   "price",
   "print",
   "prison",
   "process",
   "produce",
   "profit",
   "property",
   "prose",
   "protest",
   "pull",
   "pump",
   "punishment",
   "purpose",
   "push",
   "quarter",
   "quartz",
   "queen",
   "question",
   "quicksand",
   "quiet",
   "quill",
   "quilt",
   "quince",
   "quiver",
   "rabbit",
   "rail",
   "rain",
   "rake",
   "range",
   "rat",
   "ray",
   "reaction",
   "reading",
   "reason",
   "receipt",
   "recess",
   "record",
   "regret",
   "relation",
   "religion",
   "representative",
   "request",
   "respect",
   "rest",
   "reward",
   "rhythm",
   "rice",
   "riddle",
   "rifle",
   "ring",
   "river",
   "road",
   "robin",
   "rock",
   "rod",
   "roll",
   "roof",
   "room",
   "root",
   "rose",
   "route",
   "rub",
   "rule",
   "run",
   "sack",
   "sail",
   "salt",
   "sand",
   "scale",
   "scarecrow",
   "scarf",
   "scene",
   "scent",
   "school",
   "science",
   "scissors",
   "screw",
   "sea",
   "seat",
   "secretary",
   "seed",
   "selection",
   "self",
   "sense",
   "servant",
   "shade",
   "shake",
   "shame",
   "shape",
   "sheep",
   "sheet",
   "shelf",
   "ship",
   "shirt",
   "shock",
   "shoe",
   "shop",
   "show",
   "side",
   "sign",
   "silk",
   "silver",
   "sink",
   "sister",
   "size",
   "skate",
   "skin",
   "skirt",
   "sky",
   "slave",
   "sleep",
   "sleet",
   "slip",
   "slope",
   "smash",
   "smell",
   "smile",
   "smoke",
   "snail",
   "snake",
   "sneeze",
   "snow",
   "soap",
   "society",
   "sock",
   "soda",
   "sofa",
   "son",
   "sort",
   "sound",
   "soup",
   "space",
   "spade",
   "spark",
   "spiders",
   "sponge",
   "spoon",
   "spot",
   "spring",
   "spy",
   "square",
   "squirrel",
   "stage",
   "stamp",
   "star",
   "statement",
   "station",
   "steam",
   "steel",
   "stem",
   "step",
   "stew",
   "stick",
   "stitch",
   "stocking",
   "stomach",
   "stone",
   "stop",
   "store",
   "story",
   "stove",
   "stranger",
   "straw",
   "stream",
   "street",
   "stretch",
   "string",
   "structure",
   "substance",
   "sugar",
   "suggestion",
   "suit",
   "summer",
   "sun",
   "support",
   "surprise",
   "sweater",
   "swim",
   "swing",
   "system",
   "table",
   "tail",
   "talk",
   "tank",
   "taste",
   "tax",
   "teaching",
   "team",
   "teeth",
   "temper",
   "tendency",
   "tent",
   "territory",
   "test",
   "texture",
   "theory",
   "thing",
   "thought",
   "thread",
   "thrill",
   "throat",
   "throne",
   "thumb",
   "thunder",
   "ticket",
   "tiger",
   "time",
   "tin",
   "title",
   "toad",
   "toe",
   "tongue",
   "tooth",
   "toothpaste",
   "top",
   "touch",
   "town",
   "toy",
   "trade",
   "trail",
   "train",
   "tramp",
   "transport",
   "tray",
   "treatment",
   "tree",
   "trick",
   "trip",
   "trouble",
   "trousers",
   "truck",
   "tub",
   "turkey",
   "turn",
   "twig",
   "twist",
   "umbrella",
   "uncle",
   "underwear",
   "unit",
   "use",
   "vacation",
   "value",
   "van",
   "vase",
   "vegetable",
   "veil",
   "vein",
   "verse",
   "vessel",
   "vest",
   "view",
   "visitor",
   "voice",
   "volcano",
   "volleyball",
   "voyage",
   "walk",
   "wall",
   "war",
   "wash",
   "waste",
   "watch",
   "water",
   "wave",
   "wax",
   "way",
   "wealth",
   "weather",
   "week",
   "weight",
   "wheel",
   "whip",
   "whistle",
   "wilderness",
   "wind",
   "wine",
   "wing",
   "winter",
   "wire",
   "wish",
   "woman",
   "women",
   "wood",
   "wool",
   "word",
   "work",
   "worm",
   "wound",
   "wren",
   "wrist",
   "writer",
   "writing",
   "yak",
   "yam",
   "yard",
   "yarn",
   "year",
   "yoke",
]
