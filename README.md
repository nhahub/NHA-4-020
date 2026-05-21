# NHA-4-20
## Database Schema

```mermaid
erDiagram
    dim_groups ||--o{ dim_students : "Group_ID"
    dim_students ||--o{ fact_student_performance : "Student_Key"
    ...
```
