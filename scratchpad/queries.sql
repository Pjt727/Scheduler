SELECT * FROM Subjects WHERE Subjects.school_code like 'CC';
SELECT * FROM Subjects WHERE Subjects.code like 'CMPT';

SELECT Sections.term_year, Sections.term_season, Count(*) FROM Sections
GROUP BY Sections.term_season, Sections.term_year;


SELECT * FROM Meetings WHERE Meetings.professor_id NOT NULL;
SELECT * FROM Buildings;
SELECT * FROM Rooms;

DELETE FROM Terms;

