-- this is a comment
DELETE FROM Terms
SELECT Terms.year, Terms.season, Count(Meetings.id) FROM 
Terms LEFT JOIN Meetings ON 
Terms.year = Meetings.term_year AND Terms.season = Meetings.term_season
GROUP BY Terms.year, Terms.season

Meetings
WHERE Professors.last_name like 'Friedman '
order by Professors.last_name;

INSERT INTO Professors (id, first_name, last_name, email) 
VALUES 
(null, 'asdasdas','sadkjsahldkjsa', 'value_for_email1'),
(null, 'asdasdas','sadkjsahldkjsa', 'value_for_email1')
ON CONFLICT (email) DO NOTHING

