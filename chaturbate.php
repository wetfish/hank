#!/usr/bin/env php
<?php

error_reporting(0);

$username = isset($argv[1]) ? $argv[1] : get_username();

function main() {
    global $username;
    $url = 'https://chaturbate.com/' . urlencode($username) . '/';
    $html = get_html($url);
    $vals = extract_vals($html);
    $line = filter_chat_line(get_chat_line($vals));
    printf("<%s> %s\n", $username, $line);
}

function filter_chat_line($line) {
    $line = preg_replace('/%%%.*?%%%/', '', $line);
    $line = preg_replace('/\|\d+\|/', '', $line);
    $line = trim($line);
    if (empty($line)) {
        croak("empty line");
    }
    return $line;
}

function get_username() {
    $html = get_html('https://chaturbate.com/');
    $m = null;
    $q = "'";
    if (preg_match_all("/alt=\"([^{$q}]+){$q}s chat room\"/", $html, $m) < 1) {
        croak("get_username failed");
    }
    return $m[1][rand(0, count($m[1])-1)];
}

function get_html($url) {
    //$url = 'http://webcache.googleusercontent.com/search?q=cache:' . urlencode($url);
    $html = shell_exec(sprintf(
        "curl -s -A %s %s",
        escapeshellarg('Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.75 Safari/537.36'),
        escapeshellarg($url)
    ));
    return $html;
}

function extract_vals($html) {
    global $username;
    $v = [
        'swfUrl' => 'https://chaturbate.com/static/flash/CBV_2p648.swf',
        'pageUrl' => "https://chaturbate.com/{$username}/",
        'username' => $username,
        'port' => 1935,
    ];
    $m = null;
    preg_match("/chat_host: '([^']+)'/", $html, $m) or croak("chat_host not found");
    $v['tcUrl'] = $m[1];
    $v['host'] = str_replace('/live-chat', '', str_replace('rtmp://', '', $m[1]));
    preg_match("/username: '([^']+)'/", $html, $m) or croak("username not found");
    $v['login'] = $m[1];
    preg_match("/password: '([^']+)'/", $html, $m) or croak("pass not found");
    $v['pass'] = $m[1];
    preg_match("/'([0-9a-f]{64})'/", $html, $m) or croak("hex not found");
    $v['hex'] = $m[1];
    return $v;
}

function get_chat_line($v) {
    //echo "{$v['host']}:{$v['port']}\n";
    if (!($sock = fsockopen($v['host'], $v['port']))) {
        croak('fsockopen failed');
    }
    $c0_c1 = "\x03";
    for ($i = 0; $i < 1536; $i++) $c0_c1 .= chr(rand(0, 255));
    fwrite($sock, $c0_c1);
    fflush($sock);
    $r = 3073;
    $s0_s1_s2 = '';
    while ($r > 0) {
        $s0_s1_s2 .= fread($sock, $r);
        $r -= strlen($s0_s1_s2);
    }
    $s1 = substr($s0_s1_s2, 1, 1536);
    fwrite($sock, $s1 . get_amf0_connect($v));
    fflush($sock);
    read_until_re($sock, '/(Connection succeeded)/');
    fwrite($sock, get_amf3_join($v));
    fflush($sock);
    return read_until_re($sock, '/"m"\s*:\s*"([^"]+)",/');
}

function read_until_re($sock, $re) {
    $buf = '';
    $m = null;
    do {
        $c = fread($sock, 1);
        if ($c === false || $c === '') {
            croak("read_until_re {$re} failed");
        }
        $buf .= $c;
    } while(preg_match($re, $buf, $m) < 1);
    return $m[1];
}

function get_amf0_connect($v) {
    $o = new SabreAMF_OutputStream();
    $s = new SabreAMF_AMF0_Serializer($o);
    $s->writeAMFData('connect');
    $s->writeAMFData(1);
    $s->writeAMFData([
        'app' => 'live-chat',
        'flashVer' => 'flashVerLNX 20,0,0,306',
        'swfUrl' => $v['swfUrl'],
        'tcUrl' => $v['tcUrl'],
        'fpad' => false,
        'capabilities' => 239,
        'audioCodecs' => 3575,
        'videoCodecs' => 252,
        'videoFunction' => 1,
        'pageUrl' => $v['pageUrl'],
        'objectEncoding' => 3,
    ], 0x03);
    $s->writeAMFData('CBV,2.647');
    $s->writeAMFData($v['login']);
    $s->writeAMFData($v['pass']);
    $s->writeAMFData($v['username']);
    $s->writeAMFData($v['hex']);
    $body = $o->getRawData();
    $head  = "\x03\x00\x00\x01";
    $head .= substr(pack('N', strlen($body)), 1);
    $head .= "\x14\x00\x00\x00\x00";
    $body = str_split($body, 128);
    $chunks = count($body);
    for ($i = 0; $i < $chunks - 1; $i++) {
        $body[$i] = "{$body[$i]}\xc3";
    }
    $body = implode('', $body);
    return $head . $body;
}

function get_amf3_join($v) {
    $o = new SabreAMF_OutputStream();
    $s = new SabreAMF_AMF0_Serializer($o);
    $s->writeAMFData('joinRoom');
    $s->writeAMFData(2);
    $s->writeAMFData(null);
    $s->writeAMFData($v['username']);
    $body = $o->getRawData();
    $head  = "\x43\x00\x01\xd0";
    $head .= substr(pack('N', strlen($body)+1), 1);
    $head .= "\x11\x00";
    return $head . $body;
}

function croak($err) {
    throw new RuntimeException($err);
}

// Lol omg classes for AMF serialization
$amf = <<<'EOD'
eJztHGtz2zbyc/wrkIymkhxbku04Sa3Id34wGd35NbJ8aa/T8VAiZPFMkRqSsqI2+e+3AAgSIAE+ZCdN
p1UmpkQuFovdxe5iscQGgk97c3ODXNEmujZHPj46f38L/zu3J54bhIg/49d/zs3xvXmHY+DkSbAY8YcE
QXz/AfuB7bmo1rdq8c2xN1/59t00RCfxt8ZJE+12Oq+34c+PaOB5k9Cbo2vPWYTQPmihI8dBFDRAPg6w
/4CtVozRXIRTz0cGdBeiKw/QTcNwftBuL5fLls+QBTEu12k3E9Ide4zdMUZCi4mP8SiwWp5/146JbVPA
ALem4cxB6Pj6FJ2xO6jxCp045iLAMdo2vU5s13TQ2DGDQMng3zcYOHzG9Mbp8Pbi5vzYGLCbPdT51Ol0
s0DHl5dn/CYF2lEAXQ8H/YsPAtCuAujy+F/GyVAA2lMAnV/+p2+cnPWvONArBdDFzZlM074C6Obi1Hjf
vzBOOdBrBdDAeG8MjIsTgwO9UdHU/8k4PRoMjn6OgN5qRzc0BucR0I8KoAhJQripADo9GhrS6EYKoLPL
iw+c6xRorGTB9c3V1eVgCEygQFgB9NN5zEsGNFEADX++Mk4jARKgHZWqgLrtiZh2QFUI1JcNpnwaG7B3
e41923Ts37BfbAg0dmDvz2QHorb/Nn0HPQCpA9O1vCU3C5/u3+y2xt6snYY/xQ/YMf2vY05irPBDMCHU
emieUdnlAfSHqzm2Lkf/w2MOwgaVtVOSEuBPIXYtAUB4JhiyWJ9Y50vfDgn0qRmaSHwgfgd98s0Zmtmf
sIVqVho0emy7IapNPH+MQxiBDOHjcOG7EQbhSTv+Pl+MgONosnDHRPoSYQ3a51aCvOcuHKcpDgs+9gQ1
7OCWPGokoE0ChuRPu42OFqFn4RB4bLt3iA6JQKcha7S3iekEghUQ+ntOAdAPP6C4Z4ILOuWNYVIrZH9w
EFnkYqwjz5OwZkaTEAp9UcB/6Hokful2OLgxDnIh3h+dXRsZysAkpe9kiAUdiGlVEwq8/4gRDgLshqCe
zgp5Lvy5A2Ow+yMa2WA3QHZEmfAdGCUlDtItU8NDsJjv2Qd9/hzp5ju0vfv67au9/Vf7r3VklJMPcfVZ
PlBeIAw68Qjk/Yuh8UGLfR3eTxzPDAVNWXd4uUJ91NAymIPQh+mXIC/CzJx3CcSm75urCrygMUYXFSP2
qF0WdLxAQW3owQR/402Svo9XYNkIgc1sh/xTRPDxz0ODEa1EQZRTSQSYUzy0Z/gRXZNQS9/r+nhZpKTG
nGWzekIwe91jFls398OpD4GDi5fI+DTGc+JuGvUbdwoBhQPuibBsm+A5QHXUQnc4JD+4yNX0Rf6NeICy
djNiR+E0IooXWztu1/Y11k435HVtgUR6ZPNiVxP72K4knlo4tYPtQ5jb2JxtH1JHTlSejbgpAwdLOxxP
I24o59PYDHCuC+WABwhgzPvsIHIxJA7vURiIU12bBi5pNoqIf5Rv/dj0dtfCLK5WD5SSOfUg8MKP6kRc
yMrkX4v2fT3k4sJORk5M2aNQiwtLGfWR4D7Wwy2u22Xcl6IH4cizVjNf5bj1z2CPfUsR9RaemAsnTN+m
CHUWMljM554fgo3Um0fJFMKwJAOSzO4v+SsSxqS1FyQRDQ+ebZVfbEiCke2oxL0arB89C/R6mGNTjeHt
1eDy6qx/nfJo+aGBuPhTWsMaXQW65iwO9rcPQQTQ9oQ8uIAHDYWPYj2mWtClVcoecyPPAh+pM6Zl0HSA
Z16Ik/7g1i2F5EqgpDx/KPW6mg4FonwOGrAM9l267rW08VlZERo/DY3BxdFZ/7/GaVcVg2ykfsqKwoLF
vjvxMrm79PPPvRRR796h3VSXzFc2JLiKLlNQS3Sg4c3c9+bYD1cn3sINex11wAO+H5uEGCoIM0C1+95h
7SF3uSUhfvlSt/RRUyXzqiEjI9x6RTRZE/ykHGqCSxPOqXxYrK2aNjkcyQmJs/3cp2dkwpmv0W2cYnmo
1m/kVqrpnjiftPr3TaSlZAEzjvQeNyMNXcSvcKvl3RuMq8i30WyanYJbz7FRLgKqWCeePXvWbqMLMOLg
6c0QEV7A4hYF9mzurJCJAtO1wxUaT/H4HoF1DaeYZKx5lth07jxAPJ11BXTLKXaRYz9ghk5CEUy9hWOh
EUaWHZgjsspqeIBt4kCYwUD46st2afuWKJlmK+5nk1h/+o8y5wcwq2867IOa6DmYWbiQFZMI8TaB6DGI
Jkf4TBHqQNN6n+WfUEyltSCKheD+3i4KPZo+F3hSR80uyIGjjaiMKZjQz9uEAg74e0yIbtkkDXWC+Cwl
TZg2xEL4ktv9WGRApe4jRIeH6A0g+EwZiprdb0Q5lkW3JuU7r6qS/i1HXYqM3V0VHeVGv79207cVWwqS
E8cuDj1lIJU2K1nHZNNmKA7R5XBKs/CkMSuLdUUXV2CiGYYiK80SmKgG1ycw1JxqwJYdHdz08QQCSfji
YDeCgsBnh8pH3GJOc4M6ANa+qYSSBbmASecz/OX5xSRTwC6TiQ8uT8Atph4JygzL2u0T6lrsSezhTHBe
QeCNbTMknoo19nzkemErs0zj3LGDq4UfdceIBweSCXTJxgaQRdSBuEsQ0V04pXsZ5Ke7mGEfhnCPVwHz
cVHvKSwE/Rk40h74lgURGxlYOgIhN/sWImFwBE7UoCnoQbpBWhkogize7Ayq15sKfHHQSZhBYk5N4K8N
NGWw9DpKt7eSHsaOIjbLkAYcJwGx6Sy0CWFlGI5XVUJHhr9M7lfHZH0oyb/p5h9ROwy6TTLXGHmlUid8
H+DJsic0GydjVUxI9BHXfdB8Z2nCPAiwS9axyByHC9MRyQ+2ICSD0AqBycI+2bCXdwLTmkD0voRpE5Od
24egKjMzbNRv6s3NHYgxFNbuS24RRucpijD+usVYMdZK1ROd4vKKRCp5UB99cz7XglQow+j8XYYhzLt2
u08XjKB44FZpphjRFhZa4jooZuivUFJ6YYdi4/I1HHJpRuYpWd+SvSFVUcd6lRudTOWGqtNjz3Ow6RZ3
mS7rKOqS7DJpxrmYjbgaa3tsSPv4ZPcwXTHQLDFqtkmoIiIKlxsmcjy4ei6f3nk8kLb/yT0e2tIbh6/3
9/deF5OVVPVp+EPMvBOF6hWJ0tQkdBQ1CaquafxJtXyCSGULCT8VQV+JAobfN54944DquJTaAxaY0hVa
PtVR7QBDGgdc7Gdh46S2M8agCHxUDOkzJniCWc3jQrlqC4I35i/NyyyZaW+1wOQgEgCE8JhEg8FiPFXi
yN9UEP1FsUISaE0uNd5bySnMKELP6i90nPhIbWyAMdc5H9/ZQQjm2OLrDurBZoLz0xJZZcuniGyhGlZP
/SVxHEsbAodWlBeko+DCzfjk0uzV7LA9CdGgfCRWXQG3YKpTGiam7UAMS8lGd9jFPlggjdbHhBcRoyuQ
0Uw1iSpCELa2op1dYCXm2U7lLPz+62i+k2KUrH9kgAd8KMU1F9U6EV8tyO2EjZJ00euFvnJxmtuRXNUh
d6Qo7qiGXC6PUCCXqySqyuEsyyLCgop4xFcYlESekzhaqrao1oFcgKLo4BG45boZBW6xfKYaavE1CiXq
MwgBH6Md4osTyg4EG74m54W3LtScB4BkzaNA/7XrZ3jNuWTzSmdjE80smZJ9oixQZkZokvSSpSLq0uik
eKzY185P5JVP4pVO4H1Rka7IjuYPjxrifENI3oD6Srn2JxJsnkxp2B6lq7W1/6UFr83+YtfSzsYaxKIh
hAEgcD2MjgLa+KUmmdyo2b1Ot2a/61Ew+PbypS4gYtmLAEd8+KVm/6qtyBUoyuZYaMu1XzyoqILxO3+6
HguS2k9d1RclsL9WWd8fYmVmk+/HyoiYpOCorBgrb42moR+9OwrXUp6FbA0I26WkWbUNUNKiPGOSuOeb
M0cMuSowiNq/p+VQDn+EsO0bG4FswKhyYuXrcpHi8zVKc0VAvuJdsyi3q9SGUkVzxeszcYbkhy5RXP0U
pd3VdjBYOK9M6ekKSoJk66ZHo3ndNlNDmiQa7iXY1HWHFatU/jS7vo/biKUjbyM8m4crFEIvv3kuLsRP
94QFOSTbuRsSKzeV+3T8Gb/mHKzxV9uzTQ7QSDPyaAQSMEEHM7uvHGIYFeHQ2hcOLcwxan5aMRh0Z6HR
ioKTeAaZrsXS+0mbgMRsJhqRtT5tHpNHLnEnqT3bUluyTJ/0M+rB9BOMl4twvgivM02E6eN7ZMuTGDWG
uavt+faWng7hL4ontJqAmoL2yvNboKKR203+hCdOKjPgovXt97MRHqtQlR3xLtKOD4w8455wU0WZkuOl
5Bb30MgIRpUtLiWVbHxRNsB1vLHp0FaVBRBPGHFo6TBH6EA33KSwhECdU49/cCDjkvCILEkkmWIJ3doN
0BKTHStqo4DgB9sCelnmZUq2GxkXaNEfsV50M6tO6iLA8AGjwNjq9CBdMKniHqkhKMs7cbM4wQqXdDhL
8x3qRTJrkPuyD9ufvkfPezDvbUWZpCgZ9bkaqpo5O/260BelqOUkv+D0c/y+wnTLHos5j0i6AZqBxD0r
IO8A0BexMPgoCMS2aOEDXJjMyeafS0SNw3GLwIKTsl3TXyEW7PwdYpQ8oyvluiVp6Z23by7zPQjx3umK
EGkC2Q8krK5xRKk3FFVeiy2Kv23FuFirnZ7HzMpHA2j1CIyy/l45FlLMXzAS6l9HacA1x0E3KwkyXTQR
j4NMlEZ9XN9i4OWjij/4pav88bgwHgKtSqVoC3+FpVTRyGipF8RKWeA1F358AUev2UGCsYM5Q8f2wnqx
xeHSqSUchIZr2SYBXrgM/GTzxRb7dg3fdsmpFt008ru41XMByS87v/Z6qfcgaF4nbtDklNG3IR7IE1ed
70rmDYBUSwGW0jInDbh+3q9BkZVTtBcXIAwKLr4tmx/5FdnSiPBsLjM3SI3QFkWpEfmKFFN+bfZe2UMy
4wd/4rPx/oAzMjl/+Sul+iMkVaceZg6jVB2QKR7Noj0gUzx9RXtApnjASs4BmamTPVUHZGYO7VQdkJk5
HVJ1QGbmxErVAZmZsy9VB2Rmzgg9UtMU006BjlXMFM4VoUAnwrxjUOIJAnGHGRGn3/VWyxigro1B/4hz
SxAyDdr/D9ekoC8=
EOD;
eval(gzuncompress(base64_decode($amf)));

for ($i = 0; $i < 3; $i++) {
    try {
        main();
        break;
    } catch (RuntimeException $e) {
    }
}
