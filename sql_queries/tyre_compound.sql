-- Query 4: Tyre Compound Pace & Degradation Patterns
-- Skill: JOIN, GROUP BY, aggregations
-- Question answered: What lap-time patterns and average paces appear by compound?

SELECT 
    s.compound,
    COUNT(l.lap_number) AS total_laps_run,
    COUNT(DISTINCT s.driver_number) AS drivers_used,
    ROUND(MIN(l.lap_duration), 3) AS fastest_compound_lap,
    ROUND(AVG(l.lap_duration), 3) AS avg_compound_pace,
    ROUND(MAX(l.lap_duration), 3) AS max_compound_lap
FROM laps l
JOIN tyre_stints s 
    ON l.session_key = s.session_key 
   AND l.driver_number = s.driver_number
   AND l.lap_number BETWEEN s.lap_start AND s.lap_end
WHERE l.session_key = :session_key
  AND l.lap_duration IS NOT NULL
  AND l.is_pit_out_lap = 0
  AND s.compound IS NOT NULL
GROUP BY s.compound
ORDER BY avg_compound_pace ASC;
