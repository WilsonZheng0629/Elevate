-- Question: What should the athlete do today based on the most recent recovery, pain, soreness, and training-load information?
-- This is a decision-support heuristic, not medical advice.


WITH params AS (
    SELECT 1 AS athlete_id
),

latest_status AS (
    SELECT
        r.*,

        ROW_NUMBER() OVER (
            PARTITION BY r.athlete_id
            ORDER BY DATE(r.log_date) DESC
        ) AS latest_rank

    FROM v_recovery_status AS r

    JOIN params AS p
        ON p.athlete_id = r.athlete_id
)

SELECT
    log_date,

    readiness_score,
    recommendation,
    recommendation_reason,

    sleep_hours,
    sleep_quality_1_5,
    soreness_overall_1_10,
    knee_pain_0_10,
    ankle_pain_0_10,
    energy_1_5,
    stress_1_5,
    motivation_1_5,

    daily_training_load,
    seven_day_training_load,
    twenty_eight_day_training_load,
    load_spike_ratio,

    CASE
        WHEN recommendation = 'Train Hard'
        THEN
            'Proceed with the planned session. Maintain normal volume and intensity.'

        WHEN recommendation = 'Modify Training'
        THEN
            'Reduce lower-body volume or intensity. Prioritize technique, upper-body work, or a lighter session.'

        WHEN recommendation = 'Prioritize Recovery'
        THEN
            'Avoid hard lower-body training. Prioritize rest, mobility, light recovery work, and pain monitoring.'

        ELSE
            'Review the athlete data before making a training decision.'
    END AS recommended_action,

    CASE
        WHEN knee_pain_0_10 >= 6
          OR ankle_pain_0_10 >= 6
        THEN 'Pain flag'

        WHEN readiness_score < 50
        THEN 'Low readiness'

        WHEN soreness_overall_1_10 >= 7
        THEN 'High soreness'

        WHEN load_spike_ratio >= 1.50
        THEN 'Elevated recent load'

        WHEN sleep_hours < 7
        THEN 'Low sleep'

        ELSE 'No major warning flag'
    END AS primary_warning_flag,

    CASE
        WHEN
            sleep_hours IS NOT NULL
            AND sleep_quality_1_5 IS NOT NULL
            AND soreness_overall_1_10 IS NOT NULL
            AND energy_1_5 IS NOT NULL
            AND stress_1_5 IS NOT NULL
            AND motivation_1_5 IS NOT NULL
        THEN 'High'

        WHEN
            sleep_hours IS NOT NULL
            AND soreness_overall_1_10 IS NOT NULL
            AND energy_1_5 IS NOT NULL
        THEN 'Moderate'

        ELSE 'Low'
    END AS recommendation_confidence

FROM latest_status

WHERE latest_rank = 1;