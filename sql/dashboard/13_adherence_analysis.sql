-- Question: How consistently did the athlete complete the planned training frequency for each block?

WITH params AS (
    SELECT 1 AS athlete_id
),

block_calendar AS (
    SELECT
        tb.block_id,
        tb.athlete_id,
        tb.block_name,
        tb.start_date,
        tb.end_date,
        tb.planned_frequency_per_week,

        JULIANDAY(tb.end_date)
        - JULIANDAY(tb.start_date)
        + 1 AS block_days,

        (
            JULIANDAY(tb.end_date)
            - JULIANDAY(tb.start_date)
            + 1
        ) / 7.0 AS block_weeks

    FROM training_blocks AS tb

    JOIN params AS p
        ON p.athlete_id = tb.athlete_id
),

completed_sessions AS (
    SELECT
        ts.athlete_id,
        ts.block_id,

        COUNT(*) AS completed_sessions,

        SUM(ts.duration_minutes) AS total_training_minutes,

        SUM(ts.session_load) AS total_training_load,

        ROUND(
            AVG(ts.intensity_rpe),
            2
        ) AS average_rpe

    FROM training_sessions AS ts

    JOIN params AS p
        ON p.athlete_id = ts.athlete_id

    WHERE
        ts.completed = 1
        AND ts.block_id IS NOT NULL
        AND LOWER(ts.session_type) <> 'rest'

    GROUP BY
        ts.athlete_id,
        ts.block_id
),

adherence AS (
    SELECT
        bc.block_id,
        bc.block_name,
        bc.start_date,
        bc.end_date,
        bc.planned_frequency_per_week,

        ROUND(
            bc.block_weeks,
            2
        ) AS block_weeks,

        ROUND(
            bc.planned_frequency_per_week
            * bc.block_weeks,
            1
        ) AS expected_sessions,

        COALESCE(
            cs.completed_sessions,
            0
        ) AS completed_sessions,

        ROUND(
            100.0
            * COALESCE(cs.completed_sessions, 0)
            / NULLIF(
                bc.planned_frequency_per_week
                * bc.block_weeks,
                0
            ),
            1
        ) AS adherence_percent,

        COALESCE(
            cs.total_training_minutes,
            0
        ) AS total_training_minutes,

        COALESCE(
            cs.total_training_load,
            0
        ) AS total_training_load,

        cs.average_rpe

    FROM block_calendar AS bc

    LEFT JOIN completed_sessions AS cs
        ON cs.athlete_id = bc.athlete_id
        AND cs.block_id = bc.block_id
)

SELECT
    block_id,
    block_name,
    start_date,
    end_date,
    planned_frequency_per_week,
    block_weeks,
    expected_sessions,
    completed_sessions,
    adherence_percent,
    total_training_minutes,
    total_training_load,
    average_rpe,

    CASE
        WHEN adherence_percent >= 90
            THEN 'Excellent'

        WHEN adherence_percent >= 75
            THEN 'Good'

        WHEN adherence_percent >= 60
            THEN 'Moderate'

        ELSE 'Low'
    END AS adherence_rating

FROM adherence

ORDER BY DATE(start_date);