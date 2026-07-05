-- Am I overtraining?
SELECT
    w.log_date,
    w.sleep_hours,
    w.soreness_overall_1_10,
    w.energy_1_5,

    COALESCE(SUM(t.session_load),0) AS last_3_day_load,

    CASE
        WHEN COALESCE(SUM(t.session_load),0) > 1500
            AND w.soreness_overall_1_10 >= 7
            AND w.energy_1_5 <= 2
        THEN 'High Risk'

        WHEN COALESCE(SUM(t.session_load),0) > 1000
            AND w.soreness_overall_1_10 >= 6
        THEN 'Moderate Risk'

        ELSE 'Normal'
    END AS overtraining_flag

FROM daily_wellness w

LEFT JOIN training_sessions t
ON t.athlete_id = w.athlete_id
AND t.session_date
BETWEEN date(w.log_date,'-3 day') AND w.log_date

WHERE w.athlete_id = 1

GROUP BY
    w.log_date

ORDER BY
    w.log_date;