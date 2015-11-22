PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE learn(key text, val text, author text, created int, primary key (key, val));
CREATE TABLE auth(key text, secret text, primary key (key));
COMMIT;
