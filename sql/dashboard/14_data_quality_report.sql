-- Question: Are the source records complete, valid, and consistent enough to support the dashboard analyses?

WITH athlete_counts AS (
    SELECT
        'athletes' AS table_name,
        COUNT(*) AS total_rows,
        SUM(
            CASE
                WHEN athlete_name IS NULL
                  OR TRIM(athlete_name) = ''
                THEN 1
                ELSE 0
            END
        ) AS missing_required_values,
        0 AS invalid_range_values,
        COUNT(*) - COUNT(DISTINCT athlete_id)
            AS duplicate_key_values
    FROM athletes
),

training_block_counts AS (
    SELECT
        'training_blocks' AS table_name,
        COUNT(*) AS total_rows,
        SUM(
            CASE
                WHEN athlete_id IS NULL
                  OR block_name IS NULL
                  OR start_date IS NULL
                  OR end_date IS NULL
                THEN 1
                ELSE 0
            END
        ) AS missing_required_values,
        SUM(
            CASE
                WHEN DATE(end_date) < DATE(start_date)
                  OR planned_frequency_per_week < 0
                  OR planned_frequency_per_week > 14
                THEN 1
                ELSE 0
            END
        ) AS invalid_range_values,
        COUNT(*) - COUNT(
            DISTINCT
            athlete_id || '|'
            || block_name || '|'
            || start_date
        ) AS duplicate_key_values
    FROM training_blocks
),

wellness_counts AS (
    SELECT
        'daily_wellness' AS table_name,
        COUNT(*) AS total_rows,
        SUM(
            CASE
                WHEN athlete_id IS NULL
                  OR log_date IS NULL
                  OR sleep_hours IS NULL
                  OR sleep_quality_1_5 IS NULL
                  OR soreness_overall_1_10 IS NULL
                  OR energy_1_5 IS NULL
                  OR stress_1_5 IS NULL
                  OR motivation_1_5 IS NULL
                THEN 1
                ELSE 0
            END
        ) AS missing_required_values,
        SUM(
            CASE
                WHEN sleep_hours < 0
                  OR sleep_hours > 16
                  OR sleep_quality_1_5 NOT BETWEEN 1 AND 5
                  OR soreness_overall_1_10 NOT BETWEEN 1 AND 10
                  OR knee_pain_0_10 NOT BETWEEN 0 AND 10
                  OR ankle_pain_0_10 NOT BETWEEN 0 AND 10
                  OR energy_1_5 NOT BETWEEN 1 AND 5
                  OR stress_1_5 NOT BETWEEN 1 AND 5
                  OR motivation_1_5 NOT BETWEEN 1 AND 5
                THEN 1
                ELSE 0
            END
        ) AS invalid_range_values,
        COUNT(*) - COUNT(
            DISTINCT athlete_id || '|' || log_date
        ) AS duplicate_key_values
    FROM daily_wellness
),

session_counts AS (
    SELECT
        'training_sessions' AS table_name,
        COUNT(*) AS total_rows,
        SUM(
            CASE
                WHEN athlete_id IS NULL
                  OR session_date IS NULL
                  OR session_type IS NULL
                  OR duration_minutes IS NULL
                  OR intensity_rpe IS NULL
                  OR session_load IS NULL
                  OR completed IS NULL
                THEN 1
                ELSE 0
            END
        ) AS missing_required_values,
        SUM(
            CASE
                WHEN duration_minutes < 0
                  OR duration_minutes > 600
                  OR intensity_rpe NOT BETWEEN 0 AND 10
                  OR session_load < 0
                  OR session_load
                     <> duration_minutes * intensity_rpe
                  OR completed NOT IN (0, 1)
                THEN 1
                ELSE 0
            END
        ) AS invalid_range_values,
        COUNT(*) - COUNT(DISTINCT session_id)
            AS duplicate_key_values
    FROM training_sessions
),

exercise_counts AS (
    SELECT
        'exercise_sets' AS table_name,
        COUNT(*) AS total_rows,
        SUM(
            CASE
                WHEN session_id IS NULL
                  OR exercise_name IS NULL
                  OR set_number IS NULL
                  OR perceived_difficulty_1_10 IS NULL
                THEN 1
                ELSE 0
            END
        ) AS missing_required_values,
        SUM(
            CASE
                WHEN set_number < 1
                  OR reps < 0
                  OR weight_lb < 0
                  OR distance_yards < 0
                  OR duration_seconds < 0
                  OR jump_count < 0
                  OR perceived_difficulty_1_10
                     NOT BETWEEN 1 AND 10
                THEN 1
                ELSE 0
            END
        ) AS invalid_range_values,
        COUNT(*) - COUNT(
            DISTINCT
            session_id || '|'
            || exercise_name || '|'
            || set_number
        ) AS duplicate_key_values
    FROM exercise_sets
),

performance_counts AS (
    SELECT
        'performance_tests' AS table_name,
        COUNT(*) AS total_rows,
        SUM(
            CASE
                WHEN athlete_id IS NULL
                  OR test_date IS NULL
                  OR test_type IS NULL
                  OR metric_name IS NULL
                  OR metric_value IS NULL
                  OR unit IS NULL
                  OR attempts IS NULL
                  OR best_attempt IS NULL
                THEN 1
                ELSE 0
            END
        ) AS missing_required_values,
        SUM(
            CASE
                WHEN metric_value <= 0
                  OR attempts NOT BETWEEN 1 AND 20
                  OR best_attempt <= 0
                  OR ABS(best_attempt - metric_value) >= 0.0001
                THEN 1
                ELSE 0
            END
        ) AS invalid_range_values,
        COUNT(*) - COUNT(
            DISTINCT
            athlete_id || '|'
            || test_date || '|'
            || metric_name
        ) AS duplicate_key_values
    FROM performance_tests
),

combined AS (
    SELECT * FROM athlete_counts
    UNION ALL
    SELECT * FROM training_block_counts
    UNION ALL
    SELECT * FROM wellness_counts
    UNION ALL
    SELECT * FROM session_counts
    UNION ALL
    SELECT * FROM exercise_counts
    UNION ALL
    SELECT * FROM performance_counts
)

SELECT
    table_name,
    total_rows,
    missing_required_values,
    invalid_range_values,
    duplicate_key_values,

    missing_required_values
    + invalid_range_values
    + duplicate_key_values AS total_quality_issues,

    ROUND(
        100.0
        * (
            total_rows
            - missing_required_values
            - invalid_range_values
            - duplicate_key_values
        )
        / NULLIF(total_rows, 0),
        2
    ) AS estimated_quality_score_percent,

    CASE
        WHEN
            missing_required_values = 0
            AND invalid_range_values = 0
            AND duplicate_key_values = 0
        THEN 'Pass'

        ELSE 'Review'
    END AS quality_status

FROM combined

ORDER BY table_name;