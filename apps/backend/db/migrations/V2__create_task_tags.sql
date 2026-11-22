CREATE TABLE task_tags (
    task_id uuid NOT NULL REFERENCES tasks(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    name text COLLATE "C" NOT NULL CHECK (char_length(name) BETWEEN 1 AND 30),
    PRIMARY KEY (task_id, name)
);
