-- Where am I spending my training time?

SELECT
    session_type,
    COUNT(*) AS session_count,
    SUM(duration_minutes) AS total_minutes,
    SUM(session_load) AS total_session_load,
    ROUND(AVG(intensity_rpe), 1) AS avg_rpe
FROM training_sessions
WHERE athlete_id = 1
    AND completed = 1
GROUP BY session_type
ORDER BY total_minutes DESC;