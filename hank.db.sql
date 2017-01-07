PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE learn(key text, val text, author text, created int, primary key (key, val));
CREATE TABLE auth(key text, secret text, primary key (key));
CREATE TABLE seen(srv text, chn text, nick text, ts int, primary key (srv, chn, nick));
CREATE TABLE tell(srv text, chn text, nick text, frm text, msg text);
COMMIT;
