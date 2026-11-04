-- Query 7: Sector Bests and Theoretical Optimal Lap
-- Skill: MIN, GROUP BY, aggregations
-- Question answered: What are each driver's best individual sector times and theoretical best lap?

SELECT 
    l.driver_number,
    d.name_acronym,
    d.team_name,
    ROUND(MIN(l.duration_sector_1), 3) AS best_s1,
    ROUND(MIN(l.duration_sector_2), 3) AS best_s2,
    ROUND(MIN(l.duration_sector_3), 3) AS best_s3,
    ROUND(MIN(l.duration_sector_1) + MIN(l.duration_sector_2) + MIN(l.duration_sector_3), 3) AS theoretical_best_lap,
    ROUND(MIN(l.lap_duration), 3) AS actual_fastest_lap,
    ROUND(MIN(l.lap_duration) - (MIN(l.duration_sector_1) + MIN(l.duration_sector_2) + MIN(l.duration_sector_3)), 3) AS theoretical_delta
FROM laps l
JOIN drivers d ON l.session_key = d.session_key AND l.driver_number = d.driver_number
WHERE l.session_key = :session_key
  AND l.duration_sector_1 IS NOT NULL
  AND l.duration_sector_2 IS NOT NULL
  AND l.duration_sector_3 IS NOT NULL
  AND l.is_pit_out_lap = 0
GROUP BY l.driver_number, d.name_acronym, d.team_name
ORDER BY actual_fastest_lap ASC;
