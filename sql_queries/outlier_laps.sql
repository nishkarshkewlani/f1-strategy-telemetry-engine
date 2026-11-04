-- Query 8: Statistical Outlier Laps Detection
-- Skill: CTE, variance / delta from baseline, filtering
-- Question answered: Which laps are statistically unusual (traffic, off-track, safety-car, lockup)?

WITH driver_baseline AS (
    SELECT 
        l.driver_number,
        AVG(l.lap_duration) AS avg_lap,
        MIN(l.lap_duration) AS min_lap
    FROM laps l
    WHERE l.session_key = :session_key
      AND l.lap_duration IS NOT NULL
      AND l.is_pit_out_lap = 0
    GROUP BY l.driver_number
)
SELECT 
    l.driver_number,
    d.name_acronym,
    l.lap_number,
    ROUND(l.lap_duration, 3) AS lap_duration,
    ROUND(b.avg_lap, 3) AS driver_avg_pace,
    ROUND(l.lap_duration - b.avg_lap, 3) AS delta_from_avg,
    ROUND((l.lap_duration / b.avg_lap - 1.0) * 100, 1) AS percent_slower_than_avg,
    l.is_pit_out_lap
FROM laps l
JOIN drivers d ON l.session_key = d.session_key AND l.driver_number = d.driver_number
JOIN driver_baseline b ON l.driver_number = b.driver_number
WHERE l.session_key = :session_key
  AND l.lap_duration IS NOT NULL
  -- Laps that are more than 3.5 seconds slower than the driver's average green-flag pace
  AND (l.lap_duration - b.avg_lap) > 3.5
ORDER BY delta_from_avg DESC;
