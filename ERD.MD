erDiagram
    dim_groups ||--o{ dim_students : "Group_ID"
    dim_groups ||--o{ fact_student_performance : "Group_Key"
    dim_students ||--o{ fact_student_performance : "Student_Key"
    dim_students ||--o{ fact_test_responses : "Student_Key"
    dim_questions ||--o{ fact_test_responses : "Question_Key"
    dim_students ||--o{ fact_assessment_responses : "Student_Key"
    dim_assessment_items ||--o{ fact_assessment_responses : "Item_Key"

    dim_groups {
        int Group_Key PK
        string Group_ID
        string Group_Type
    }

    dim_students {
        int Student_Key PK
        string Student_ID
        string Group_ID FK
    }

    dim_questions {
        int Question_Key PK
        int Question_Number
        string Test_Type
    }

    dim_assessment_items {
        int Item_Key PK
        int Item_Number
        string Item_Type
        string Phase
    }

    fact_student_performance {
        int Fact_ID PK
        int Student_Key FK
        int Group_Key FK
        int Total_Pre_Test
        int Total_Post_Test
        int Test_Knowledge_Gain
        int Total_Pre_Enjoyment
        int Total_Post_Enjoyment
        int Total_Passion
        float Passion_Learning_Efficiency
    }

    fact_test_responses {
        int Response_ID PK
        int Student_Key FK
        int Question_Key FK
        int Response
    }

    fact_assessment_responses {
        int Assessment_ID PK
        int Student_Key FK
        int Item_Key FK
        int Response
    }