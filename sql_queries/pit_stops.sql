-- Query 6: Pit-Stop Duration & Frequency Summary
-- Skill: COUNT, AVG, MIN, MAX, GROUP BY
-- Question answered: How many stops occurred, when did they happen, and what was observed stop loss?

SELECT 
    p.driver_number,
    d.name_acronym,
    d.team_name,
    COUNT(p.lap_number) AS total_pit_stops,
    GROUP_CONCAT(p.lap_number, ', ') AS pit_laps,
    ROUND(AVG(p.pit_duration), 3) AS avg_pit_duration,
    ROUND(MIN(p.pit_duration), 3) AS fastest_pit_duration,
    ROUND(MAX(p.pit_duration), 3) AS longest_pit_duration
FROM pit_stops p
JOIN drivers d ON p.session_key = d.session_key AND p.driver_number = d.driver_number
WHERE p.session_key = :session_key
GROUP BY p.driver_number, d.name_acronym, d.team_name
ORDER BY total_pit_stops DESC, avg_pit_duration ASC;
