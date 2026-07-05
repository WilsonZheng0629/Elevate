-- How much training work is one athlete doing each week?

SELECT
    strftime('%Y-%W', session_date) AS training_week,
    session_type,
    SUM(session_load) AS total_session_load,
    SUM(duration_minutes) AS total_minutes,
    ROUND(AVG(intensity_rpe), 1) AS avg_rpe,
    COUNT(*) AS session_count
FROM training_sessions
WHERE athlete_id = 1
  AND completed = 1
GROUP BY
    training_week,
    session_type
ORDER BY
    training_week,
    session_type;