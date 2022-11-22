CREATE TABLE event (
  id text NOT NULL CONSTRAINT event_pk PRIMARY KEY,
  created_at int NOT NULL,
  pubkey text NOT NULL,
  kind int NOT NULL,
  content text NOT NULL,
  tags jsonb NOT NULL,
  sig text NOT NULL
);

CREATE INDEX ON event USING btree(pubkey);
