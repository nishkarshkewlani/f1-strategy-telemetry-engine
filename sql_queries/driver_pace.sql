-- Query 1: Driver Average and Fastest Lap
-- Skill: GROUP BY, MIN, AVG, HAVING
-- Question answered: Who had the best average race pace and single-lap fastest pace?

SELECT 
    d.driver_number,
    d.name_acronym,
    d.team_name,
    COUNT(l.lap_number) AS completed_laps,
    ROUND(MIN(l.lap_duration), 3) AS fastest_lap_seconds,
    ROUND(AVG(l.lap_duration), 3) AS avg_lap_seconds
FROM laps l
JOIN drivers d ON l.session_key = d.session_key AND l.driver_number = d.driver_number
WHERE l.session_key = :session_key
  AND l.lap_duration IS NOT NULL
  AND l.is_pit_out_lap = 0
GROUP BY d.driver_number, d.name_acronym, d.team_name
HAVING COUNT(l.lap_number) >= 5
ORDER BY avg_lap_seconds ASC;
