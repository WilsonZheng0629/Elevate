-- which training block worked best

SELECT
    b.block_name,
    b.block_focus,
    MIN(p.metric_value) AS starting_vertical,
    MAX(p.metric_value) AS best_vertical,
    MAX(p.metric_value) - MIN(p.metric_value) AS vertical_gain,
    COUNT(DISTINCT t.session_id) AS total_sessions,
    SUM(t.session_load) AS total_training_load,
    ROUND(AVG(t.intensity_rpe),1) AS avg_rpe
FROM training_blocks b
LEFT JOIN performance_tests p
    ON b.block_id = p.block_id
LEFT JOIN training_sessions t
    ON b.block_id = t.block_id
WHERE b.athlete_id = 1
    AND p.metric_name = 'approach_vertical'
GROUP BY
    b.block_id,
    b.block_name,
    b.block_focus
ORDER BY vertical_gain DESC;