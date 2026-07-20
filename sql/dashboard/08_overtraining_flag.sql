-- Question: Is recent training stress elevated?

WITH params AS (
    SELECT 1 AS athlete_id
)

SELECT
    r.log_date,
    r.sleep_hours,
    r.soreness_overall_1_10,
    r.energy_1_5,

    r.seven_day_training_load,
    r.twenty_eight_day_training_load,
    r.load_spike_ratio,

    r.readiness_score,

    CASE
        WHEN
            r.knee_pain_0_10 >= 6
            OR r.ankle_pain_0_10 >= 6
            OR r.readiness_score < 50
        THEN 'High'

        WHEN
            r.readiness_score < 70
            OR r.soreness_overall_1_10 >= 7
            OR r.load_spike_ratio >= 1.50
        THEN 'Moderate'

        ELSE 'Normal'
    END AS training_stress_flag,

    r.recommendation,
    r.recommendation_reason

FROM v_recovery_status AS r

JOIN params AS p
    ON p.athlete_id = r.athlete_id

ORDER BY DATE(r.log_date);