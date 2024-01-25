
# TODO List

## Onboarding New 'status' Table

**Task:** Implement the addition of the new 'status' table during onboarding.

**SQL Commands:**

```sql
CREATE TABLE status (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    enabled BOOLEAN
);
INSERT INTO status (enabled) VALUES (TRUE);
```

**Status:** ✅ Completed

---

This task has been successfully implemented and is now part of the database schema setup.
