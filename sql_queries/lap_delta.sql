-- Query 2: Lap-to-Lap Pace Delta
-- Skill: LAG() OVER (PARTITION BY ... ORDER BY ...)
-- Question answered: How did each lap compare with the previous lap for a given driver?

SELECT 
    l.lap_number,
    l.lap_duration,
    ROUND(LAG(l.lap_duration, 1) OVER (
        PARTITION BY l.driver_number ORDER BY l.lap_number
    ), 3) AS prev_lap_duration,
    ROUND(l.lap_duration - LAG(l.lap_duration, 1) OVER (
        PARTITION BY l.driver_number ORDER BY l.lap_number
    ), 3) AS delta_to_prev_seconds,
    l.is_pit_out_lap
FROM laps l
WHERE l.session_key = :session_key
  AND l.driver_number = :driver_number
  AND l.lap_duration IS NOT NULL
ORDER BY l.lap_number ASC;
