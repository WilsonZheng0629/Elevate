-- Question:
-- Under which recovery and training conditions does the athlete
-- produce their strongest jump performances?

WITH params AS (
    SELECT
        1 AS athlete_id,
        'approach_vertical' AS metric_name
),

jump_tests AS (
    SELECT
        pt.test_id,
        pt.athlete_id,
        pt.block_id,
        pt.test_date,
        pt.metric_name,
        pt.metric_value,
        pt.unit,
        pt.test_context,
        pt.surface,
        pt.shoes,
        pt.warmup_quality_1_5,

        -- Rank each performance relative to the athlete's other
        -- tests for the same metric.
        PERCENT_RANK() OVER (
            PARTITION BY
                pt.athlete_id,
                pt.metric_name
            ORDER BY pt.metric_value
        ) AS performance_percentile,

        AVG(pt.metric_value) OVER (
            PARTITION BY
                pt.athlete_id,
                pt.metric_name
        ) AS athlete_average_jump,

        MAX(pt.metric_value) OVER (
            PARTITION BY
                pt.athlete_id,
                pt.metric_name
        ) AS athlete_personal_best

    FROM performance_tests AS pt

    JOIN params AS p
        ON p.athlete_id = pt.athlete_id
        AND p.metric_name = pt.metric_name
),

previous_night_wellness AS (
    SELECT
        jt.test_id,

        dw.sleep_hours AS previous_night_sleep_hours,
        dw.sleep_quality_1_5 AS previous_night_sleep_quality

    FROM jump_tests AS jt

    LEFT JOIN daily_wellness AS dw
        ON dw.athlete_id = jt.athlete_id
        AND DATE(dw.log_date) = DATE(
            jt.test_date,
            '-1 day'
        )
),

same_day_wellness AS (
    SELECT
        jt.test_id,

        dw.soreness_overall_1_10,
        dw.knee_pain_0_10,
        dw.ankle_pain_0_10,
        dw.energy_1_5,
        dw.stress_1_5,
        dw.motivation_1_5,
        dw.bodyweight_lb,
        dw.resting_hr

    FROM jump_tests AS jt

    LEFT JOIN daily_wellness AS dw
        ON dw.athlete_id = jt.athlete_id
        AND DATE(dw.log_date) = DATE(jt.test_date)
),

previous_session_candidates AS (
    SELECT
        jt.test_id,
        ts.session_id,
        ts.session_date,
        ts.session_type,
        ts.session_focus,
        ts.duration_minutes,
        ts.intensity_rpe,
        ts.session_load,

        JULIANDAY(jt.test_date)
        - JULIANDAY(ts.session_date)
            AS days_since_previous_session,

        ROW_NUMBER() OVER (
            PARTITION BY jt.test_id
            ORDER BY
                DATE(ts.session_date) DESC,
                ts.session_id DESC
        ) AS session_rank

    FROM jump_tests AS jt

    LEFT JOIN training_sessions AS ts
        ON ts.athlete_id = jt.athlete_id
        AND ts.completed = 1
        AND DATE(ts.session_date) < DATE(jt.test_date)
),

previous_session AS (
    SELECT
        test_id,
        session_id AS previous_session_id,
        session_date AS previous_session_date,
        session_type AS previous_session_type,
        session_focus AS previous_session_focus,
        duration_minutes AS previous_session_duration,
        intensity_rpe AS previous_session_rpe,
        session_load AS previous_session_load,
        days_since_previous_session

    FROM previous_session_candidates

    WHERE session_rank = 1
),

combined AS (
    SELECT
        jt.test_id,
        jt.athlete_id,
        jt.block_id,
        jt.test_date,
        jt.metric_name,
        jt.metric_value,
        jt.unit,

        ROUND(
            jt.performance_percentile * 100,
            1
        ) AS performance_percentile,

        ROUND(
            jt.athlete_average_jump,
            2
        ) AS athlete_average_jump,

        jt.athlete_personal_best,

        ROUND(
            jt.metric_value
            - jt.athlete_average_jump,
            2
        ) AS difference_from_average,

        CASE
            WHEN jt.metric_value = jt.athlete_personal_best
                THEN 'Personal Best'

            WHEN jt.performance_percentile >= 0.75
                THEN 'Top 25%'

            WHEN jt.performance_percentile <= 0.25
                THEN 'Bottom 25%'

            ELSE 'Middle 50%'
        END AS performance_group,

        pnw.previous_night_sleep_hours,
        pnw.previous_night_sleep_quality,

        sdw.soreness_overall_1_10,
        sdw.knee_pain_0_10,
        sdw.ankle_pain_0_10,
        sdw.energy_1_5,
        sdw.stress_1_5,
        sdw.motivation_1_5,
        sdw.bodyweight_lb,
        sdw.resting_hr,

        ps.previous_session_date,
        ps.previous_session_type,
        ps.previous_session_focus,
        ps.previous_session_duration,
        ps.previous_session_rpe,
        ps.previous_session_load,
        ps.days_since_previous_session,

        jt.test_context,
        jt.surface,
        jt.shoes,
        jt.warmup_quality_1_5

    FROM jump_tests AS jt

    LEFT JOIN previous_night_wellness AS pnw
        ON pnw.test_id = jt.test_id

    LEFT JOIN same_day_wellness AS sdw
        ON sdw.test_id = jt.test_id

    LEFT JOIN previous_session AS ps
        ON ps.test_id = jt.test_id
)

SELECT
    *

FROM combined

ORDER BY
    metric_value DESC,
    DATE(test_date) DESC;