-- Query 9: Pre- and Post-Pit Stop Pace Comparison
-- Skill: CTE, Window functions, conditional aggregation
-- Question answered: How did pace differ immediately before and after a pit stop (undercut/overcut delta)?

WITH pit_laps AS (
    SELECT 
        session_key,
        driver_number,
        lap_number AS pit_lap,
        pit_duration
    FROM pit_stops
    WHERE session_key = :session_key
),
stint_context AS (
    SELECT 
        l.session_key,
        l.driver_number,
        d.name_acronym,
        p.pit_lap,
        p.pit_duration,
        -- Lap before pit (in-lap approach)
        MAX(CASE WHEN l.lap_number = p.pit_lap - 1 THEN l.lap_duration END) AS pre_pit_lap,
        -- Pit lap itself (in-lap)
        MAX(CASE WHEN l.lap_number = p.pit_lap THEN l.lap_duration END) AS in_lap_time,
        -- Lap after pit (out-lap)
        MAX(CASE WHEN l.lap_number = p.pit_lap + 1 THEN l.lap_duration END) AS out_lap_time,
        -- Flying lap on fresh tyres
        MAX(CASE WHEN l.lap_number = p.pit_lap + 2 THEN l.lap_duration END) AS post_pit_flying_lap
    FROM pit_laps p
    JOIN laps l 
        ON p.session_key = l.session_key 
       AND p.driver_number = l.driver_number
       AND l.lap_number BETWEEN p.pit_lap - 1 AND p.pit_lap + 2
    JOIN drivers d 
        ON l.session_key = d.session_key 
       AND l.driver_number = d.driver_number
    GROUP BY l.session_key, l.driver_number, d.name_acronym, p.pit_lap, p.pit_duration
)
SELECT 
    driver_number,
    name_acronym,
    pit_lap,
    ROUND(pit_duration, 3) AS pit_lane_duration,
    ROUND(pre_pit_lap, 3) AS pre_pit_pace,
    ROUND(in_lap_time, 3) AS in_lap_pace,
    ROUND(out_lap_time, 3) AS out_lap_pace,
    ROUND(post_pit_flying_lap, 3) AS post_pit_fresh_pace,
    ROUND(pre_pit_lap - post_pit_flying_lap, 3) AS fresh_tyre_delta
FROM stint_context
WHERE pre_pit_lap IS NOT NULL AND post_pit_flying_lap IS NOT NULL
ORDER BY pit_lap ASC, driver_number ASC;
