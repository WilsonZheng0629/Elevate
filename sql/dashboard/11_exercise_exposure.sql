-- Question: Which exercises appear most often in training, and what performance changes are observed during blocks that include those exercises?
-- Important: This analysis shows association, not causation.

WITH params AS (
    SELECT
        1 AS athlete_id,
        'approach_vertical' AS metric_name
),

exercise_block_exposure AS (
    SELECT
        ts.athlete_id,
        ts.block_id,
        es.exercise_name,

        COUNT(DISTINCT ts.session_id) AS sessions_with_exercise,

        COUNT(*) AS total_sets,

        SUM(
            COALESCE(es.reps, 0)
        ) AS total_reps,

        SUM(
            COALESCE(es.jump_count, 0)
        ) AS total_jump_contacts,

        ROUND(
            AVG(es.perceived_difficulty_1_10),
            2
        ) AS average_exercise_difficulty,

        SUM(
            CASE
                WHEN es.weight_lb IS NOT NULL
                     AND es.reps IS NOT NULL
                THEN es.weight_lb * es.reps
                ELSE 0
            END
        ) AS total_volume_lb

    FROM training_sessions AS ts

    JOIN exercise_sets AS es
        ON es.session_id = ts.session_id

    JOIN params AS p
        ON p.athlete_id = ts.athlete_id

    WHERE
        ts.completed = 1
        AND ts.block_id IS NOT NULL

    GROUP BY
        ts.athlete_id,
        ts.block_id,
        es.exercise_name
),

block_performance AS (
    SELECT
        tbp.athlete_id,
        tbp.block_id,
        tbp.block_name,
        tbp.metric_name,
        tbp.starting_performance,
        tbp.ending_performance,
        tbp.absolute_improvement,
        tbp.percentage_improvement,
        tbp.total_training_load

    FROM v_training_block_performance AS tbp

    JOIN params AS p
        ON p.athlete_id = tbp.athlete_id
        AND p.metric_name = tbp.metric_name
),

exercise_block_results AS (
    SELECT
        ebe.athlete_id,
        ebe.block_id,
        bp.block_name,
        ebe.exercise_name,

        ebe.sessions_with_exercise,
        ebe.total_sets,
        ebe.total_reps,
        ebe.total_jump_contacts,
        ebe.average_exercise_difficulty,
        ebe.total_volume_lb,

        bp.starting_performance,
        bp.ending_performance,
        bp.absolute_improvement,
        bp.percentage_improvement,
        bp.total_training_load

    FROM exercise_block_exposure AS ebe

    LEFT JOIN block_performance AS bp
        ON bp.athlete_id = ebe.athlete_id
        AND bp.block_id = ebe.block_id
),

exercise_summary AS (
    SELECT
        exercise_name,

        COUNT(DISTINCT block_id) AS blocks_exposed,

        SUM(sessions_with_exercise) AS total_sessions_with_exercise,

        SUM(total_sets) AS total_sets,

        SUM(total_reps) AS total_reps,

        SUM(total_jump_contacts) AS total_jump_contacts,

        ROUND(
            AVG(average_exercise_difficulty),
            2
        ) AS average_exercise_difficulty,

        ROUND(
            SUM(total_volume_lb),
            1
        ) AS total_volume_lb,

        ROUND(
            AVG(absolute_improvement),
            2
        ) AS average_block_improvement,

        ROUND(
            AVG(percentage_improvement),
            2
        ) AS average_block_improvement_percent,

        ROUND(
            SUM(absolute_improvement * sessions_with_exercise)
            / NULLIF(
                SUM(sessions_with_exercise),
                0
            ),
            2
        ) AS exposure_weighted_improvement,

        ROUND(
            AVG(
                absolute_improvement
                / NULLIF(total_training_load, 0)
                * 1000
            ),
            3
        ) AS average_improvement_per_1000_load

    FROM exercise_block_results

    GROUP BY exercise_name
)

SELECT
    exercise_name,
    blocks_exposed,
    total_sessions_with_exercise,
    total_sets,
    total_reps,
    total_jump_contacts,
    average_exercise_difficulty,
    total_volume_lb,
    average_block_improvement,
    average_block_improvement_percent,
    exposure_weighted_improvement,
    average_improvement_per_1000_load,

    CASE
        WHEN total_sessions_with_exercise >= 10
            THEN 'High exposure'

        WHEN total_sessions_with_exercise >= 5
            THEN 'Moderate exposure'

        ELSE 'Low exposure'
    END AS exposure_level

FROM exercise_summary

ORDER BY
    exposure_weighted_improvement DESC,
    total_sessions_with_exercise DESC;