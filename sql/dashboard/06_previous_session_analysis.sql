-- what workout before my last jump test?

SELECT
    p.test_date,
    p.metric_value AS approach_vertical,
    t.session_date,
    t.session_type,
    t.session_focus,
    t.session_load,
    t.intensity_rpe
FROM performance_tests p
LEFT JOIN training_sessions t
ON t.session_date = (
    SELECT MAX(session_date)
    FROM training_sessions
    WHERE athlete_id = p.athlete_id
      AND session_date < p.test_date
)
WHERE p.athlete_id = 1
    AND p.metric_name = 'approach_vertical'
ORDER BY p.test_date;