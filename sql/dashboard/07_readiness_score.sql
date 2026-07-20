-- Question: How ready is the athlete to train?

WITH params AS (
    SELECT 1 AS athlete_id
)

SELECT
    r.log_date,

    r.sleep_hours,
    r.sleep_quality_1_5,
    r.soreness_overall_1_10,
    r.knee_pain_0_10,
    r.ankle_pain_0_10,
    r.energy_1_5,
    r.stress_1_5,
    r.motivation_1_5,

    r.daily_training_load,
    r.seven_day_training_load,
    r.twenty_eight_day_training_load,
    r.load_spike_ratio,

    r.readiness_score,
    r.recommendation,
    r.recommendation_reason

FROM v_recovery_status AS r

JOIN params AS p
    ON p.athlete_id = r.athlete_id

ORDER BY DATE(r.log_date);
