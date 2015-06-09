import weechat
import random
import urllib
import json

weechat.register("hankbot", "ceph", "1.1", "GPL3", "hankbot", "", "")

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, " \
    "like Gecko) Chrome/39.0.2171.95 Safari/537.36"
UNPROVOKED_ODDS = 100
PROVOKED_ODDS = 5
INSULT_ODDS = 2

def escapeshellarg(arg):
    return "\\'".join("'" + p + "'" for p in arg.split("'"))

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
    pieces = line.split(" ", 1)
    tokn, rest = (pieces if len(pieces) == 2 else (line, ""))
    if tokn == "?im":
        run_im(srv, chn, rest)
    elif tokn == "?ir":
        run_im(srv, chn, rest, shuf=True)
    elif tokn == "?yt":
        run_yt(srv, chn, rest)
    elif tokn == "?tw":
        run_tw(srv, chn, rest)
    elif tokn == "?tu":
        run_im(srv, chn, rest, pre_q="site:tumblr.com ")
    elif tokn == "?rl" or random.randint(1, UNPROVOKED_ODDS) == 1:
        run_wf(srv, chn)
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
    elif mynick.lower() in line.lower() and \
        random.randint(1, PROVOKED_ODDS) == 1:
        run_insult(srv, chn) if random.randint(1, INSULT_ODDS) == 1 \
        else run_compliment(srv, chn)
    return weechat.WEECHAT_RC_OK

def run_co(srv, chn, lang, code):
    url = "http://codepad.org"
    run_curl(srv, chn, url, """ack --no-color -A10 '^<pre>$' | """ \
        """lynx -stdin -dump | """ \
        """awk 'BEGIN{s=1} /References/{s=0} {if (s==1)print $0}' | """ \
        """xargs echo""", "%s", \
        "lang=%s&code=%s&private=True&run=True&submit=Submit" % \
        (urllib.quote(lang), urllib.quote(code)))

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

def run_tw(srv, chn, q):
    url = "https://twitter.com/search?" + \
        urllib.urlencode({
            "f": "realtime",
            "q": q
        })
    run_curl(srv, chn, url, \
        """grep -Po '(?<=data-aria-label-part="0">).*?(?=</p>)' | """ \
        """sed -e 's/<[^>]*>//g' | recode -f html..ascii | head -n1""", "%s")

def run_wf(srv, chn):
    logfile = '~/.weechat/logs/irc.%s.%s.weechatlog' % (srv, chn)
    cmd = '''tail -c "+$[ 1 + $[ RANDOM % $(stat -c '%s' ''' + \
        logfile + \
        ''') ]]" ''' + \
        logfile + \
        '''| head -n21 | tail -n20 2>/dev/null | ''' \
        '''grep -Pv '(-->|<--)' | shuf -n1 | cut -f3-'''
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
        buffer = weechat.info_get("irc_buffer", \
            udata['srv'] + "," + udata['chn'])
        if not buffer:
            return weechat.WEECHAT_RC_OK
        if rci == 0:
            curl_stdout = curl_stdout.strip()
            curl_stdout = ''.join([i if ord(i) < 128 else '?' for i in curl_stdout])
            if curl_stdout != "":
                weechat.command(buffer, "/say " + (fmt % (curl_stdout)))
            else:
                weechat.command(buffer, ":/")
        else:
            weechat.command(buffer, ":(")
        curl_stdout = ""
        curl_stderr = ""
    return weechat.WEECHAT_RC_OK

weechat.hook_signal("*,irc_in2_privmsg", "msg_cb", "");
