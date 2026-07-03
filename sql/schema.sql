CREATE TABLE IF NOT EXISTS athletes (
    athlete_id INTEGER PRIMARY KEY,
    athlete_name TEXT NOT NULL,
    sport TEXT,
    position TEXT,
    height_in REAL,
    bodyweight_start_lb REAL,
    standing_reach_in REAL,
    primary_goal TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS training_blocks (
    block_id INTEGER PRIMARY KEY,
    athlete_id INTEGER,
    block_name TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    block_focus TEXT,
    planned_frequency_per_week INTEGER,
    notes TEXT,
    FOREIGN KEY (athlete_id) REFERENCES athletes(athlete_id)
);

CREATE TABLE IF NOT EXISTS daily_wellness (
    wellness_id INTEGER PRIMARY KEY,
    athlete_id INTEGER,
    log_date TEXT NOT NULL,
    sleep_hours REAL,
    sleep_quality_1_5 INTEGER,
    soreness_overall_1_10 INTEGER,
    knee_pain_0_10 INTEGER,
    ankle_pain_0_10 INTEGER,
    energy_1_5 INTEGER,
    stress_1_5 INTEGER,
    motivation_1_5 INTEGER,
    bodyweight_lb REAL,
    resting_hr INTEGER,
    notes TEXT,
    FOREIGN KEY (athlete_id) REFERENCES athletes(athlete_id)
);

CREATE TABLE IF NOT EXISTS training_sessions (
    session_id INTEGER PRIMARY KEY,
    athlete_id INTEGER,
    block_id INTEGER,
    session_date TEXT NOT NULL,
    session_type TEXT NOT NULL,
    session_focus TEXT,
    duration_minutes INTEGER,
    intensity_rpe INTEGER,
    session_load INTEGER,
    location TEXT,
    completed INTEGER,
    notes TEXT,
    FOREIGN KEY (athlete_id) REFERENCES athletes(athlete_id),
    FOREIGN KEY (block_id) REFERENCES training_blocks(block_id)
);

CREATE TABLE IF NOT EXISTS exercise_sets (
    set_id INTEGER PRIMARY KEY,
    session_id INTEGER,
    exercise_name TEXT NOT NULL,
    exercise_category TEXT,
    set_number INTEGER,
    reps INTEGER,
    weight_lb REAL,
    distance_yards REAL,
    duration_seconds REAL,
    jump_count INTEGER,
    perceived_difficulty_1_10 INTEGER,
    notes TEXT,
    FOREIGN KEY (session_id) REFERENCES training_sessions(session_id)
);

CREATE TABLE IF NOT EXISTS performance_tests (
    test_id INTEGER PRIMARY KEY,
    athlete_id INTEGER,
    block_id INTEGER,
    test_date TEXT NOT NULL,
    test_type TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    unit TEXT,
    test_context TEXT,
    attempts INTEGER,
    best_attempt REAL,
    surface TEXT,
    shoes TEXT,
    warmup_quality_1_5 INTEGER,
    notes TEXT,
    FOREIGN KEY (athlete_id) REFERENCES athletes(athlete_id),
    FOREIGN KEY (block_id) REFERENCES training_blocks(block_id)
);