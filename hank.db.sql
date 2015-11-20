PRAGMA foreign_keys=OFF;
BEGIN TRANSACTION;
CREATE TABLE learn(key text, val text, author text, created int, primary key (key, val));
COMMIT;
