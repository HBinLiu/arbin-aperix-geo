-- One-time: unify Lexical blockType slugs in rich text `body` columns.
-- Canonical slugs: brief, callout, highlight, figure, infoGrid, chapter, inlineCta
--
-- Run (from repo root):
--   psql "$DATABASE_URL" -f payload/scripts/migrate-content-block-slugs.sql
--
-- Idempotent: safe to re-run; already-migrated rows are unchanged.

BEGIN;

CREATE OR REPLACE FUNCTION pg_temp.migrate_content_block_slugs(input jsonb)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
  result text;
  pairs constant text[][] := ARRAY[
    ARRAY['"blockType":"newsBrief"',      '"blockType":"brief"'],
    ARRAY['"blockType":"blogBrief"',      '"blockType":"brief"'],
    ARRAY['"blockType":"academyBrief"',   '"blockType":"brief"'],
    ARRAY['"blockType":"newsCallout"',    '"blockType":"callout"'],
    ARRAY['"blockType":"blogCallout"',    '"blockType":"callout"'],
    ARRAY['"blockType":"academyCallout"', '"blockType":"callout"'],
    ARRAY['"blockType":"newsHighlight"',    '"blockType":"highlight"'],
    ARRAY['"blockType":"blogHighlight"',    '"blockType":"highlight"'],
    ARRAY['"blockType":"academyHighlight"', '"blockType":"highlight"'],
    ARRAY['"blockType":"researchCallout"',  '"blockType":"highlight"'],
    ARRAY['"blockType":"newsFigure"',      '"blockType":"figure"'],
    ARRAY['"blockType":"blogFigure"',      '"blockType":"figure"'],
    ARRAY['"blockType":"academyFigure"',   '"blockType":"figure"'],
    ARRAY['"blockType":"researchFigure"',  '"blockType":"figure"'],
    ARRAY['"blockType":"newsInfoGrid"',    '"blockType":"infoGrid"'],
    ARRAY['"blockType":"blogInfoGrid"',    '"blockType":"infoGrid"'],
    ARRAY['"blockType":"academyInfoGrid"', '"blockType":"infoGrid"'],
    ARRAY['"blockType":"newsLead"',        '"blockType":"chapter"'],
    ARRAY['"blockType":"blogLead"',        '"blockType":"chapter"'],
    ARRAY['"blockType":"academyLead"',    '"blockType":"chapter"'],
    ARRAY['"blockType":"researchLead"',    '"blockType":"chapter"'],
    ARRAY['"blockType":"lead"',            '"blockType":"chapter"'],
    ARRAY['"blockType":"newsInlineCta"',    '"blockType":"inlineCta"'],
    ARRAY['"blockType":"blogInlineCta"',    '"blockType":"inlineCta"'],
    ARRAY['"blockType":"academyInlineCta"', '"blockType":"inlineCta"'],
    ARRAY['"blockType":"researchInlineCta"', '"blockType":"inlineCta"']
  ];
  pair text[];
BEGIN
  IF input IS NULL THEN
    RETURN NULL;
  END IF;

  result := input::text;
  FOREACH pair SLICE 1 IN ARRAY pairs
  LOOP
    result := replace(result, pair[1], pair[2]);
  END LOOP;

  RETURN result::jsonb;
END;
$$;

DO $$
DECLARE
  tables constant text[] := ARRAY[
    'news',
    'news_versions',
    'blogs',
    'blogs_versions',
    'academies',
    'academies_versions',
    'researches',
    'researches_versions'
  ];
  tbl text;
  updated bigint;
BEGIN
  FOREACH tbl IN ARRAY tables
  LOOP
    IF to_regclass(format('public.%I', tbl)) IS NULL THEN
      RAISE NOTICE 'skip missing table: %', tbl;
      CONTINUE;
    END IF;

    EXECUTE format(
      'UPDATE %I SET body = pg_temp.migrate_content_block_slugs(body) WHERE body IS NOT NULL',
      tbl,
    );
    GET DIAGNOSTICS updated = ROW_COUNT;
    RAISE NOTICE 'updated % rows in %', updated, tbl;
  END LOOP;
END;
$$;

COMMIT;
