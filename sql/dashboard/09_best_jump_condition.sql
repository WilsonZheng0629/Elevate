-- Under what conditions do I jump the highest?

SELECT
    p.test_date,
    p.metric_value AS approach_vertical,
    w.sleep_hours,
    w.sleep_quality_1_5,
    w.soreness_overall_1_10,
    w.energy_1_5,
    w.stress_1_5,
    w.motivation_1_5,
    w.knee_pain_0_10,
    w.ankle_pain_0_10
FROM performance_tests p
JOIN daily_wellness w
    ON p.athlete_id = w.athlete_id
    AND p.test_date = w.log_date
WHERE p.athlete_id = 1
    AND p.metric_name = 'approach_vertical'
ORDER BY approach_vertical DESC;