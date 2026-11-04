-- Query 3: Driver Pace Ranking
-- Skill: RANK() OVER (ORDER BY ...)
-- Question answered: How do drivers rank by representative green-flag pace?

WITH clean_driver_pace AS (
    SELECT 
        l.driver_number,
        d.name_acronym,
        d.team_name,
        COUNT(l.lap_number) AS total_laps,
        AVG(l.lap_duration) AS mean_pace,
        MIN(l.lap_duration) AS best_lap
    FROM laps l
    JOIN drivers d ON l.session_key = d.session_key AND l.driver_number = d.driver_number
    WHERE l.session_key = :session_key
      AND l.lap_duration IS NOT NULL
      AND l.is_pit_out_lap = 0
    GROUP BY l.driver_number, d.name_acronym, d.team_name
    HAVING COUNT(l.lap_number) >= 10
)
SELECT 
    RANK() OVER (ORDER BY mean_pace ASC) AS pace_rank,
    driver_number,
    name_acronym,
    team_name,
    total_laps,
    ROUND(mean_pace, 3) AS avg_lap_time,
    ROUND(best_lap, 3) AS fastest_lap,
    ROUND(mean_pace - FIRST_VALUE(mean_pace) OVER (ORDER BY mean_pace ASC), 3) AS gap_to_leader_avg
FROM clean_driver_pace
ORDER BY pace_rank ASC;
