-- Am I improving my vertical jump?

SELECT 
    test_date, 
    athlete_id, 
    metric_value AS approach_vertical, 
    unit
FROM performance_tests
WHERE metric_name = 'approach_vertical'
ORDER BY athlete_id, test_date;