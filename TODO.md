Need to implement adding new 'status' table into onboarding

CREATE TABLE status (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    enabled BOOLEAN
);
INSERT INTO status (enabled) VALUES (TRUE);

