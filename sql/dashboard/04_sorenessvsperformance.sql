-- Does soreness affect performance?

SELECT
    p.test_date,
    p.metric_value AS approach_vertical,
    w.soreness_overall_1_10,
    w.knee_pain_0_10,
    w.ankle_pain_0_10
FROM performance_tests p
JOIN daily_wellness w
    ON p.test_date = w.log_date
    AND p.athlete_id = w.athlete_id
WHERE p.athlete_id = 1
    AND p.metric_name = 'approach_vertical'
ORDER BY p.test_date;