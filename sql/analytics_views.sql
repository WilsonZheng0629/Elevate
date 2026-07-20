-- ============================================================
-- Elevate Analytical Views
-- SQLite
-- ============================================================

PRAGMA foreign_keys = ON;


-- ============================================================
-- 1. SESSION LOAD VIEW
-- One row per completed training session.
-- ============================================================

DROP VIEW IF EXISTS v_session_load;

CREATE VIEW v_session_load AS
SELECT
    ts.session_id,
    ts.athlete_id,
    ts.block_id,
    ts.session_date,
    ts.session_type,
    ts.session_focus,
    ts.duration_minutes,
    ts.intensity_rpe,
    ts.session_load,
    ts.location,
    ts.completed,

    SUM(ts.session_load) OVER (
        PARTITION BY ts.athlete_id
        ORDER BY JULIANDAY(ts.session_date)
        RANGE BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS seven_day_training_load,

    SUM(ts.session_load) OVER (
        PARTITION BY ts.athlete_id
        ORDER BY JULIANDAY(ts.session_date)
        RANGE BETWEEN 27 PRECEDING AND CURRENT ROW
    ) AS twenty_eight_day_training_load

FROM training_sessions AS ts
WHERE ts.completed = 1;


-- ============================================================
-- 2. JUMP TEST SUMMARY
-- One row per athlete, date, and jump metric.
-- The current dataset stores one summarized test result per row,
-- so metric_value and best_attempt should match.
-- ============================================================

DROP VIEW IF EXISTS v_jump_session_best;

CREATE VIEW v_jump_session_best AS
SELECT
    pt.test_id,
    pt.athlete_id,
    pt.block_id,
    pt.test_date,
    pt.test_type,
    pt.metric_name,
    pt.metric_value,
    pt.unit,
    pt.attempts,
    pt.best_attempt,
    pt.test_context,
    pt.surface,
    pt.shoes,
    pt.warmup_quality_1_5,

    MAX(pt.metric_value) OVER (
        PARTITION BY
            pt.athlete_id,
            pt.metric_name
    ) AS personal_best,

    AVG(pt.metric_value) OVER (
        PARTITION BY
            pt.athlete_id,
            pt.metric_name
        ORDER BY pt.test_date
        ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
    ) AS three_test_rolling_average,

    pt.metric_value
    -
    LAG(pt.metric_value) OVER (
        PARTITION BY
            pt.athlete_id,
            pt.metric_name
        ORDER BY pt.test_date
    ) AS change_from_previous_test

FROM performance_tests AS pt;


-- ============================================================
-- 3. DAILY FEATURE SET
-- One row per athlete per wellness date.
-- Combines wellness, same-day load, recent load, and any
-- performance test recorded on that date.
-- ============================================================

DROP VIEW IF EXISTS v_daily_feature_set;

CREATE VIEW v_daily_feature_set AS
WITH daily_session_load AS (
    SELECT
        athlete_id,
        session_date,
        SUM(session_load) AS daily_training_load,
        COUNT(*) AS sessions_completed
    FROM training_sessions
    WHERE completed = 1
    GROUP BY
        athlete_id,
        session_date
),

daily_performance AS (
    SELECT
        athlete_id,
        test_date,
        MAX(
            CASE
                WHEN metric_name = 'approach_jump'
                THEN metric_value
            END
        ) AS approach_jump_value,

        MAX(
            CASE
                WHEN metric_name = 'cmj'
                THEN metric_value
            END
        ) AS cmj_value
    FROM performance_tests
    GROUP BY
        athlete_id,
        test_date
),

base_features AS (
    SELECT
        dw.wellness_id,
        dw.athlete_id,
        dw.log_date,

        dw.sleep_hours,
        dw.sleep_quality_1_5,
        dw.soreness_overall_1_10,
        dw.knee_pain_0_10,
        dw.ankle_pain_0_10,
        dw.energy_1_5,
        dw.stress_1_5,
        dw.motivation_1_5,
        dw.bodyweight_lb,
        dw.resting_hr,

        COALESCE(
            dsl.daily_training_load,
            0
        ) AS daily_training_load,

        COALESCE(
            dsl.sessions_completed,
            0
        ) AS sessions_completed,

        dp.approach_jump_value,
        dp.cmj_value

    FROM daily_wellness AS dw

    LEFT JOIN daily_session_load AS dsl
        ON dsl.athlete_id = dw.athlete_id
        AND dsl.session_date = dw.log_date

    LEFT JOIN daily_performance AS dp
        ON dp.athlete_id = dw.athlete_id
        AND dp.test_date = dw.log_date
)

SELECT
    bf.*,

    LAG(bf.sleep_hours, 1) OVER (
        PARTITION BY bf.athlete_id
        ORDER BY bf.log_date
    ) AS previous_day_sleep_hours,

    LAG(bf.soreness_overall_1_10, 1) OVER (
        PARTITION BY bf.athlete_id
        ORDER BY bf.log_date
    ) AS previous_day_soreness,

    LAG(bf.daily_training_load, 1) OVER (
        PARTITION BY bf.athlete_id
        ORDER BY bf.log_date
    ) AS previous_day_training_load,

    SUM(bf.daily_training_load) OVER (
        PARTITION BY bf.athlete_id
        ORDER BY JULIANDAY(bf.log_date)
        RANGE BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS seven_day_training_load,

    SUM(bf.daily_training_load) OVER (
        PARTITION BY bf.athlete_id
        ORDER BY JULIANDAY(bf.log_date)
        RANGE BETWEEN 27 PRECEDING AND CURRENT ROW
    ) AS twenty_eight_day_training_load

FROM base_features AS bf;


-- ============================================================
-- 4. TRAINING BLOCK PERFORMANCE
-- One row per athlete and training block.
-- Training and performance are aggregated separately before
-- being joined. This prevents duplicated session-load totals.
-- ============================================================

DROP VIEW IF EXISTS v_training_block_performance;

CREATE VIEW v_training_block_performance AS
WITH block_training AS (
    SELECT
        ts.athlete_id,
        ts.block_id,

        COUNT(*) AS completed_sessions,

        SUM(ts.session_load) AS total_training_load,

        AVG(ts.intensity_rpe) AS average_session_rpe,

        SUM(ts.duration_minutes) AS total_training_minutes

    FROM training_sessions AS ts

    WHERE
        ts.completed = 1
        AND ts.block_id IS NOT NULL

    GROUP BY
        ts.athlete_id,
        ts.block_id
),

ranked_tests AS (
    SELECT
        pt.test_id,
        pt.athlete_id,
        pt.block_id,
        pt.test_date,
        pt.metric_name,
        pt.metric_value,

        ROW_NUMBER() OVER (
            PARTITION BY
                pt.athlete_id,
                pt.block_id,
                pt.metric_name
            ORDER BY
                pt.test_date ASC,
                pt.test_id ASC
        ) AS first_test_rank,

        ROW_NUMBER() OVER (
            PARTITION BY
                pt.athlete_id,
                pt.block_id,
                pt.metric_name
            ORDER BY
                pt.test_date DESC,
                pt.test_id DESC
        ) AS last_test_rank

    FROM performance_tests AS pt

    WHERE pt.block_id IS NOT NULL
),

block_performance AS (
    SELECT
        athlete_id,
        block_id,
        metric_name,

        COUNT(*) AS test_count,

        MAX(
            CASE
                WHEN first_test_rank = 1
                THEN metric_value
            END
        ) AS starting_performance,

        MAX(
            CASE
                WHEN last_test_rank = 1
                THEN metric_value
            END
        ) AS ending_performance,

        MAX(metric_value) AS best_performance,

        AVG(metric_value) AS average_performance

    FROM ranked_tests

    GROUP BY
        athlete_id,
        block_id,
        metric_name
)

SELECT
    tb.block_id,
    tb.athlete_id,
    tb.block_name,
    tb.start_date,
    tb.end_date,
    tb.block_focus,
    tb.planned_frequency_per_week,

    bp.metric_name,
    bp.test_count,
    bp.starting_performance,
    bp.ending_performance,
    bp.best_performance,
    bp.average_performance,

    ROUND(
        bp.ending_performance
        - bp.starting_performance,
        2
    ) AS absolute_improvement,

    ROUND(
        100.0
        * (
            bp.ending_performance
            - bp.starting_performance
        )
        / NULLIF(
            bp.starting_performance,
            0
        ),
        2
    ) AS percentage_improvement,

    COALESCE(
        bt.completed_sessions,
        0
    ) AS completed_sessions,

    COALESCE(
        bt.total_training_load,
        0
    ) AS total_training_load,

    ROUND(
        bt.average_session_rpe,
        2
    ) AS average_session_rpe,

    COALESCE(
        bt.total_training_minutes,
        0
    ) AS total_training_minutes,

    ROUND(
        (
            bp.ending_performance
            - bp.starting_performance
        )
        / NULLIF(
            bt.total_training_load,
            0
        )
        * 1000,
        3
    ) AS improvement_per_1000_load

FROM training_blocks AS tb

LEFT JOIN block_training AS bt
    ON bt.athlete_id = tb.athlete_id
    AND bt.block_id = tb.block_id

LEFT JOIN block_performance AS bp
    ON bp.athlete_id = tb.athlete_id
    AND bp.block_id = tb.block_id;


-- ============================================================
-- 5. RECOVERY STATUS
-- One row per athlete per wellness date.
-- Readiness score is normalized from 0 to 100.
-- ============================================================

DROP VIEW IF EXISTS v_recovery_status;

CREATE VIEW v_recovery_status AS
WITH readiness_components AS (
    SELECT
        dfs.*,

        MIN(
            dfs.sleep_hours / 9.0,
            1.0
        ) * 100 AS sleep_duration_score,

        (
            (
                dfs.sleep_quality_1_5 - 1.0
            ) / 4.0
        ) * 100 AS sleep_quality_score,

        (
            (
                dfs.energy_1_5 - 1.0
            ) / 4.0
        ) * 100 AS energy_score,

        (
            (
                dfs.motivation_1_5 - 1.0
            ) / 4.0
        ) * 100 AS motivation_score,

        (
            (
                5.0 - dfs.stress_1_5
            ) / 4.0
        ) * 100 AS inverse_stress_score,

        (
            (
                10.0 - dfs.soreness_overall_1_10
            ) / 9.0
        ) * 100 AS inverse_soreness_score

    FROM v_daily_feature_set AS dfs
),

readiness_scores AS (
    SELECT
        rc.*,

        ROUND(
            (
                rc.sleep_duration_score * 0.20
                +
                rc.sleep_quality_score * 0.15
                +
                rc.energy_score * 0.20
                +
                rc.motivation_score * 0.10
                +
                rc.inverse_stress_score * 0.15
                +
                rc.inverse_soreness_score * 0.20
            ),
            1
        ) AS readiness_score,

        CASE
            WHEN rc.twenty_eight_day_training_load > 0
            THEN ROUND(
                rc.seven_day_training_load
                /
                (
                    rc.twenty_eight_day_training_load
                    / 4.0
                ),
                2
            )
            ELSE NULL
        END AS load_spike_ratio

    FROM readiness_components AS rc
)

SELECT
    rs.*,

    CASE
        WHEN
            rs.knee_pain_0_10 >= 6
            OR rs.ankle_pain_0_10 >= 6
        THEN 'Prioritize Recovery'

        WHEN rs.readiness_score < 50
        THEN 'Prioritize Recovery'

        WHEN
            rs.readiness_score < 70
            OR rs.soreness_overall_1_10 >= 7
            OR rs.load_spike_ratio >= 1.50
        THEN 'Modify Training'

        ELSE 'Train Hard'
    END AS recommendation,

    CASE
        WHEN
            rs.knee_pain_0_10 >= 6
            OR rs.ankle_pain_0_10 >= 6
        THEN 'High pain score reported'

        WHEN rs.readiness_score < 50
        THEN 'Low readiness score'

        WHEN rs.soreness_overall_1_10 >= 7
        THEN 'High overall soreness'

        WHEN rs.load_spike_ratio >= 1.50
        THEN 'Recent training load is elevated'

        WHEN rs.readiness_score < 70
        THEN 'Moderate readiness score'

        ELSE 'Recovery indicators support normal training'
    END AS recommendation_reason

FROM readiness_scores AS rs;