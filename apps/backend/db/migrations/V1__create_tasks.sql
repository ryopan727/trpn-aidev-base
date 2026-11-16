CREATE TABLE tasks (
    id uuid PRIMARY KEY,
    title text NOT NULL CHECK (char_length(title) BETWEEN 1 AND 100),
    status text NOT NULL CHECK (status IN ('pending', 'completed')),
    created_at timestamptz NOT NULL
);

CREATE INDEX tasks_created_at_id_idx ON tasks (created_at DESC, id DESC);
