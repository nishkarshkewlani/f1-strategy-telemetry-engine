-- Query 5: Stint Length Analysis
-- Skill: Arithmetic, joins, ordering
-- Question answered: Which stints were longest and how did compounds endure?

SELECT 
    s.driver_number,
    d.name_acronym,
    d.team_name,
    s.stint_number,
    s.compound,
    s.lap_start,
    s.lap_end,
    (s.lap_end - s.lap_start + 1) AS stint_length_laps,
    s.tyre_age_at_start,
    (s.lap_end - s.lap_start + 1 + s.tyre_age_at_start) AS final_tyre_age
FROM tyre_stints s
JOIN drivers d ON s.session_key = d.session_key AND s.driver_number = d.driver_number
WHERE s.session_key = :session_key
ORDER BY stint_length_laps DESC, s.stint_number ASC;
