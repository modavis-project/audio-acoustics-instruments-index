PRAGMA foreign_keys = ON;
PRAGMA application_id = 1094797641;
PRAGMA user_version = 10000;

CREATE TABLE metadata (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE categories (
  category_id TEXT PRIMARY KEY,
  label_en TEXT NOT NULL,
  label_de TEXT NOT NULL,
  broader TEXT NOT NULL,
  definition_en TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE repositories (
  catalogue_id TEXT PRIMARY KEY,
  full_name TEXT NOT NULL COLLATE NOCASE UNIQUE,
  owner TEXT NOT NULL,
  name TEXT NOT NULL,
  html_url TEXT NOT NULL UNIQUE,
  description_de TEXT NOT NULL,
  primary_category TEXT NOT NULL REFERENCES categories(category_id),
  scope_status TEXT NOT NULL CHECK (scope_status IN ('core', 'adjacent')),
  snapshot_date TEXT NOT NULL,
  record_status TEXT NOT NULL CHECK (record_status IN ('active', 'merged')),
  redirects_to TEXT REFERENCES repositories(catalogue_id) DEFERRABLE INITIALLY DEFERRED
) WITHOUT ROWID;

CREATE TABLE github_snapshots (
  catalogue_id TEXT PRIMARY KEY REFERENCES repositories(catalogue_id),
  repository_id INTEGER UNIQUE,
  node_id TEXT UNIQUE,
  status TEXT NOT NULL CHECK (status IN ('available', 'unavailable', 'merged', 'error')),
  queried_full_name TEXT NOT NULL,
  name_with_owner TEXT,
  url TEXT,
  homepage_url TEXT,
  description TEXT,
  is_archived INTEGER,
  is_disabled INTEGER,
  is_fork INTEGER,
  default_branch TEXT,
  primary_language TEXT,
  license_spdx TEXT,
  stargazers_count INTEGER,
  forks_count INTEGER,
  open_issues_count INTEGER,
  created_at TEXT,
  pushed_at TEXT,
  updated_at TEXT,
  captured_at TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE topics (
  catalogue_id TEXT NOT NULL REFERENCES repositories(catalogue_id),
  topic TEXT NOT NULL,
  PRIMARY KEY (catalogue_id, topic)
) WITHOUT ROWID;

CREATE TABLE repository_aliases (
  catalogue_id TEXT NOT NULL REFERENCES repositories(catalogue_id),
  alias_full_name TEXT NOT NULL COLLATE NOCASE UNIQUE,
  alias_url TEXT NOT NULL UNIQUE,
  current_full_name TEXT NOT NULL,
  PRIMARY KEY (catalogue_id, alias_full_name)
) WITHOUT ROWID;

CREATE INDEX repositories_category_idx ON repositories(primary_category);
CREATE INDEX repositories_scope_idx ON repositories(scope_status);
CREATE INDEX topics_topic_idx ON topics(topic);

CREATE VIEW repository_current AS
SELECT
  r.catalogue_id,
  COALESCE(g.name_with_owner, r.full_name) AS full_name,
  COALESCE(g.url, r.html_url) AS html_url,
  g.description,
  r.description_de,
  r.primary_category,
  c.label_en AS category_label_en,
  c.label_de AS category_label_de,
  r.scope_status,
  r.record_status,
  r.redirects_to,
  g.repository_id AS github_repository_id,
  g.status AS github_status,
  g.is_archived,
  g.is_disabled,
  g.is_fork,
  g.primary_language,
  g.license_spdx,
  g.stargazers_count,
  g.forks_count,
  g.open_issues_count,
  r.snapshot_date,
  g.captured_at
FROM repositories AS r
JOIN categories AS c ON c.category_id = r.primary_category
LEFT JOIN github_snapshots AS g ON g.catalogue_id = r.catalogue_id;

CREATE VIRTUAL TABLE repository_search USING fts5(
  catalogue_id UNINDEXED,
  full_name,
  description,
  description_de,
  category,
  topics,
  tokenize = 'unicode61 remove_diacritics 2'
);
