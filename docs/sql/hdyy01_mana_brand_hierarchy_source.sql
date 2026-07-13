-- ETL must stage the extracted rows before loading the reporting dimension.
-- Reject a level3_code with conflicting parent/grade values.
-- Replace target only after validation succeeds.
SELECT
    level1.MBID AS level1_code,
    level1.MBCNAME AS level1_name,
    level2.MBID AS level2_code,
    level2.MBCNAME AS level2_name,
    level3.MBID AS level3_code,
    level3.MBCNAME AS level3_name,
    level3.MBSTR1 AS grade_code,
    CASE level3.MBSTR1
        WHEN '1' THEN 'A'
        WHEN '2' THEN 'B'
        WHEN '3' THEN 'C'
        WHEN '4' THEN 'D'
    END AS grade_label,
    CURRENT_TIMESTAMP AS etl_loaded_at
FROM BIBH.ODS_MANABRAND level3
JOIN BIBH.ODS_MANABRAND level2
    ON level3.MBPID = level2.MBID
    AND level2.MBCLASS = 2
JOIN BIBH.ODS_MANABRAND level1
    ON level2.MBPID = level1.MBID
    AND level1.MBCLASS = 1
WHERE level3.MBCLASS = 3;
