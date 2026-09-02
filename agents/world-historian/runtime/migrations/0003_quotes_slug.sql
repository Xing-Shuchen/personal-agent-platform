-- 0003_quotes_slug.sql: slug for standalone source-material files in the vault
ALTER TABLE quotes ADD COLUMN slug TEXT;
