-- How ready am I to train today?

SELECT
    log_date,
    sleep_hours,
    sleep_quality_1_5,
    soreness_overall_1_10,
    knee_pain_0_10,
    ankle_pain_0_10,
    energy_1_5,
    stress_1_5,
    motivation_1_5,

    ROUND(
        (
            sleep_quality_1_5 * 20
            + energy_1_5 * 20
            + motivation_1_5 * 10
            - soreness_overall_1_10 * 4
            - knee_pain_0_10 * 3
            - ankle_pain_0_10 * 3
            - stress_1_5 * 5
        ),1
    ) AS readiness_score

FROM daily_wellness
WHERE athlete_id = 1
ORDER BY log_date;
