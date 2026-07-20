-- ============================================================
-- Elevate Database Schema
-- SQLite
-- ============================================================

-- SQLite does not enforce foreign keys unless this is enabled.
PRAGMA foreign_keys = ON;


-- ============================================================
-- 1. ATHLETES
-- One row per athlete.
-- ============================================================

CREATE TABLE IF NOT EXISTS athletes (
    athlete_id INTEGER PRIMARY KEY,

    athlete_name TEXT NOT NULL
        CHECK (LENGTH(TRIM(athlete_name)) > 0),

    sport TEXT NOT NULL
        DEFAULT 'Volleyball'
        CHECK (LENGTH(TRIM(sport)) > 0),

    position TEXT,

    height_in REAL
        CHECK (
            height_in IS NULL
            OR height_in BETWEEN 48 AND 96
        ),

    bodyweight_start_lb REAL
        CHECK (
            bodyweight_start_lb IS NULL
            OR bodyweight_start_lb BETWEEN 50 AND 500
        ),

    standing_reach_in REAL
        CHECK (
            standing_reach_in IS NULL
            OR standing_reach_in BETWEEN 48 AND 144
        ),

    primary_goal TEXT,

    created_at TEXT NOT NULL
        DEFAULT CURRENT_TIMESTAMP
        CHECK (
            DATE(created_at) IS NOT NULL
            OR DATETIME(created_at) IS NOT NULL
        )
);


-- ============================================================
-- 2. TRAINING BLOCKS
-- One row per athlete training phase.
-- ============================================================

CREATE TABLE IF NOT EXISTS training_blocks (
    block_id INTEGER PRIMARY KEY,

    athlete_id INTEGER NOT NULL,

    block_name TEXT NOT NULL
        CHECK (LENGTH(TRIM(block_name)) > 0),

    start_date TEXT NOT NULL
        CHECK (DATE(start_date) IS NOT NULL),

    end_date TEXT NOT NULL
        CHECK (DATE(end_date) IS NOT NULL),

    block_focus TEXT,

    planned_frequency_per_week INTEGER
        CHECK (
            planned_frequency_per_week IS NULL
            OR planned_frequency_per_week BETWEEN 0 AND 14
        ),

    notes TEXT,

    FOREIGN KEY (athlete_id)
        REFERENCES athletes(athlete_id)
        ON UPDATE CASCADE
        ON DELETE RESTRICT,

    CHECK (DATE(end_date) >= DATE(start_date)),

    UNIQUE (
        athlete_id,
        block_name,
        start_date
    )
);


-- ============================================================
-- 3. DAILY WELLNESS
-- Maximum one wellness entry per athlete per date.
-- ============================================================

CREATE TABLE IF NOT EXISTS daily_wellness (
    wellness_id INTEGER PRIMARY KEY,

    athlete_id INTEGER NOT NULL,

    log_date TEXT NOT NULL
        CHECK (DATE(log_date) IS NOT NULL),

    sleep_hours REAL NOT NULL
        CHECK (sleep_hours BETWEEN 0 AND 16),

    sleep_quality_1_5 INTEGER NOT NULL
        CHECK (sleep_quality_1_5 BETWEEN 1 AND 5),

    soreness_overall_1_10 INTEGER NOT NULL
        CHECK (soreness_overall_1_10 BETWEEN 1 AND 10),

    knee_pain_0_10 INTEGER NOT NULL
        DEFAULT 0
        CHECK (knee_pain_0_10 BETWEEN 0 AND 10),

    ankle_pain_0_10 INTEGER NOT NULL
        DEFAULT 0
        CHECK (ankle_pain_0_10 BETWEEN 0 AND 10),

    energy_1_5 INTEGER NOT NULL
        CHECK (energy_1_5 BETWEEN 1 AND 5),

    stress_1_5 INTEGER NOT NULL
        CHECK (stress_1_5 BETWEEN 1 AND 5),

    motivation_1_5 INTEGER NOT NULL
        CHECK (motivation_1_5 BETWEEN 1 AND 5),

    bodyweight_lb REAL
        CHECK (
            bodyweight_lb IS NULL
            OR bodyweight_lb BETWEEN 50 AND 500
        ),

    resting_hr INTEGER
        CHECK (
            resting_hr IS NULL
            OR resting_hr BETWEEN 30 AND 220
        ),

    notes TEXT,

    FOREIGN KEY (athlete_id)
        REFERENCES athletes(athlete_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    UNIQUE (
        athlete_id,
        log_date
    )
);


-- ============================================================
-- 4. TRAINING SESSIONS
-- One row per workout or rest-day record.
-- ============================================================

CREATE TABLE IF NOT EXISTS training_sessions (
    session_id INTEGER PRIMARY KEY,

    athlete_id INTEGER NOT NULL,

    block_id INTEGER,

    session_date TEXT NOT NULL
        CHECK (DATE(session_date) IS NOT NULL),

    session_type TEXT NOT NULL
        CHECK (LENGTH(TRIM(session_type)) > 0),

    session_focus TEXT,

    duration_minutes INTEGER NOT NULL
        CHECK (duration_minutes BETWEEN 0 AND 600),

    intensity_rpe INTEGER NOT NULL
        CHECK (intensity_rpe BETWEEN 0 AND 10),

    session_load INTEGER NOT NULL
        CHECK (session_load >= 0),

    location TEXT,

    completed INTEGER NOT NULL
        DEFAULT 1
        CHECK (completed IN (0, 1)),

    notes TEXT,

    FOREIGN KEY (athlete_id)
        REFERENCES athletes(athlete_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    FOREIGN KEY (block_id)
        REFERENCES training_blocks(block_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL,

    -- Session load must equal duration × RPE.
    CHECK (
        session_load = duration_minutes * intensity_rpe
    ),

    -- Zero-minute and zero-RPE records should only represent rest.
    CHECK (
        (
            LOWER(session_type) = 'rest'
            AND duration_minutes = 0
            AND intensity_rpe = 0
            AND session_load = 0
        )
        OR
        (
            LOWER(session_type) <> 'rest'
            AND duration_minutes > 0
            AND intensity_rpe > 0
        )
    )
);


-- ============================================================
-- 5. EXERCISE SETS
-- One row per exercise set completed within a session.
-- ============================================================

CREATE TABLE IF NOT EXISTS exercise_sets (
    set_id INTEGER PRIMARY KEY,

    session_id INTEGER NOT NULL,

    exercise_name TEXT NOT NULL
        CHECK (LENGTH(TRIM(exercise_name)) > 0),

    exercise_category TEXT,

    set_number INTEGER NOT NULL
        CHECK (set_number >= 1),

    reps INTEGER
        CHECK (
            reps IS NULL
            OR reps >= 0
        ),

    weight_lb REAL
        CHECK (
            weight_lb IS NULL
            OR weight_lb >= 0
        ),

    distance_yards REAL
        CHECK (
            distance_yards IS NULL
            OR distance_yards >= 0
        ),

    duration_seconds REAL
        CHECK (
            duration_seconds IS NULL
            OR duration_seconds >= 0
        ),

    jump_count INTEGER
        CHECK (
            jump_count IS NULL
            OR jump_count >= 0
        ),

    perceived_difficulty_1_10 INTEGER NOT NULL
        CHECK (
            perceived_difficulty_1_10 BETWEEN 1 AND 10
        ),

    notes TEXT,

    FOREIGN KEY (session_id)
        REFERENCES training_sessions(session_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    UNIQUE (
        session_id,
        exercise_name,
        set_number
    ),

    -- At least one measurable exercise value should be recorded.
    CHECK (
        reps IS NOT NULL
        OR weight_lb IS NOT NULL
        OR distance_yards IS NOT NULL
        OR duration_seconds IS NOT NULL
        OR jump_count IS NOT NULL
    )
);


-- ============================================================
-- 6. PERFORMANCE TESTS
-- One row per summarized performance-test result.
-- ============================================================

CREATE TABLE IF NOT EXISTS performance_tests (
    test_id INTEGER PRIMARY KEY,

    athlete_id INTEGER NOT NULL,

    block_id INTEGER,

    test_date TEXT NOT NULL
        CHECK (DATE(test_date) IS NOT NULL),

    test_type TEXT NOT NULL
        CHECK (LENGTH(TRIM(test_type)) > 0),

    metric_name TEXT NOT NULL
        CHECK (LENGTH(TRIM(metric_name)) > 0),

    metric_value REAL NOT NULL
        CHECK (metric_value > 0),

    unit TEXT NOT NULL
        CHECK (LENGTH(TRIM(unit)) > 0),

    test_context TEXT,

    attempts INTEGER NOT NULL
        CHECK (attempts BETWEEN 1 AND 20),

    best_attempt REAL NOT NULL
        CHECK (best_attempt > 0),

    surface TEXT,

    shoes TEXT,

    warmup_quality_1_5 INTEGER
        CHECK (
            warmup_quality_1_5 IS NULL
            OR warmup_quality_1_5 BETWEEN 1 AND 5
        ),

    notes TEXT,

    FOREIGN KEY (athlete_id)
        REFERENCES athletes(athlete_id)
        ON UPDATE CASCADE
        ON DELETE CASCADE,

    FOREIGN KEY (block_id)
        REFERENCES training_blocks(block_id)
        ON UPDATE CASCADE
        ON DELETE SET NULL,

    CHECK (
        ABS(best_attempt - metric_value) < 0.0001
    ),

    UNIQUE (
        athlete_id,
        test_date,
        metric_name
    )
);


-- ============================================================
-- INDEXES
-- Improve filtering, joins, and dashboard query performance.
-- ============================================================

CREATE INDEX IF NOT EXISTS idx_training_blocks_athlete_dates
ON training_blocks (
    athlete_id,
    start_date,
    end_date
);


CREATE INDEX IF NOT EXISTS idx_daily_wellness_athlete_date
ON daily_wellness (
    athlete_id,
    log_date
);


CREATE INDEX IF NOT EXISTS idx_training_sessions_athlete_date
ON training_sessions (
    athlete_id,
    session_date
);


CREATE INDEX IF NOT EXISTS idx_training_sessions_block
ON training_sessions (
    block_id
);


CREATE INDEX IF NOT EXISTS idx_training_sessions_type
ON training_sessions (
    session_type
);


CREATE INDEX IF NOT EXISTS idx_exercise_sets_session
ON exercise_sets (
    session_id
);


CREATE INDEX IF NOT EXISTS idx_exercise_sets_name
ON exercise_sets (
    exercise_name
);


CREATE INDEX IF NOT EXISTS idx_performance_tests_athlete_date
ON performance_tests (
    athlete_id,
    test_date
);


CREATE INDEX IF NOT EXISTS idx_performance_tests_block
ON performance_tests (
    block_id
);


CREATE INDEX IF NOT EXISTS idx_performance_tests_metric
ON performance_tests (
    metric_name
);