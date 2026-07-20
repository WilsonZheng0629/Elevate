-- Question:
-- How is the athlete's training time and workload distributed across session types?

WITH params AS (
    SELECT
        1 AS athlete_id
),

session_summary AS (
    SELECT
        ts.athlete_id,
        ts.session_type,

        COUNT(*) AS session_count,

        SUM(ts.duration_minutes) AS total_minutes,

        SUM(ts.session_load) AS total_training_load,

        ROUND(
            AVG(ts.duration_minutes),
            1
        ) AS average_duration_minutes,

        ROUND(
            AVG(ts.intensity_rpe),
            1
        ) AS average_rpe,

        ROUND(
            AVG(ts.session_load),
            1
        ) AS average_session_load

    FROM training_sessions AS ts

    JOIN params AS p
        ON p.athlete_id = ts.athlete_id

    WHERE ts.completed = 1

    GROUP BY
        ts.athlete_id,
        ts.session_type
),

totals AS (
    SELECT
        athlete_id,

        SUM(session_count) AS all_sessions,

        SUM(total_minutes) AS all_minutes,

        SUM(total_training_load) AS all_training_load

    FROM session_summary

    GROUP BY athlete_id
)

SELECT
    ss.session_type,

    ss.session_count,

    ROUND(
        100.0 * ss.session_count
        / NULLIF(t.all_sessions, 0),
        1
    ) AS percentage_of_sessions,

    ss.total_minutes,

    ROUND(
        100.0 * ss.total_minutes
        / NULLIF(t.all_minutes, 0),
        1
    ) AS percentage_of_training_time,

    ss.total_training_load,

    ROUND(
        100.0 * ss.total_training_load
        / NULLIF(t.all_training_load, 0),
        1
    ) AS percentage_of_training_load,

    ss.average_duration_minutes,
    ss.average_rpe,
    ss.average_session_load

FROM session_summary AS ss

JOIN totals AS t
    ON t.athlete_id = ss.athlete_id

ORDER BY
    ss.total_training_load DESC;