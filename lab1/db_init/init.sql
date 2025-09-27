CREATE SCHEMA IF NOT EXISTS lab1;

CREATE TYPE complexity AS ENUM ('easy', 'normal', 'hard');

CREATE TABLE lab1.dishes (
	id SERIAL PRIMARY KEY,
	dishname VARCHAR(64) NOT NULL,
	cook_complexity complexity NOT NULL,
	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO lab1.dishes(dishname, cook_complexity) VALUES
('солянка', 'normal'),
('копченые ребра', 'hard'),
('пельмени', 'normal'),
('чизбургер', 'easy'),
('лазанья', 'hard');