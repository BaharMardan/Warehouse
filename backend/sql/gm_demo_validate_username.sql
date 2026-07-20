-- Throwaway function ONLY to prove the golden-master pipeline.
-- Pure: no DB reads, deterministic. Safe to drop later.
CREATE OR REPLACE FUNCTION gm_demo_validate_username(p_user_name IN VARCHAR2)
RETURN VARCHAR2
IS
BEGIN
  IF p_user_name IS NULL OR TRIM(p_user_name) IS NULL THEN RETURN 'EMPTY'; END IF;
  IF LENGTH(TRIM(p_user_name)) < 3 THEN RETURN 'TOO_SHORT'; END IF;
  IF NOT REGEXP_LIKE(p_user_name, '^[a-zA-Z0-9._@\-]+$') THEN RETURN 'INVALID_CHARS'; END IF;
  RETURN 'OK';
END;
/
