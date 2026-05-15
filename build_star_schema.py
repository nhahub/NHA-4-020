# build_star_schema.py
# Project : AI-Enhanced Educational Analytics (DEPI R4)
# Milestone: M2 - SQL Integration & Security

import pandas as pd
import sqlite3
import hashlib
import os

# CONFIG 
INPUT_CSV  = 'Final_Refined_Project_Data.csv'
OUTPUT_DIR = 'star_schema_output'
DB_NAME    = 'educational_analytics.db'
os.makedirs(OUTPUT_DIR, exist_ok=True)

# LOAD DATA 
print("Loading data...")
df = pd.read_csv(INPUT_CSV)
print(f"  Loaded {df.shape[0]} students, {df.shape[1]} columns")

# ANONYMIZATION (Privacy / Data Governance)
def anonymize_id(student_id):
    return 'anon_' + hashlib.sha256(str(student_id).encode()).hexdigest()[:10]

df['Anon_Student_ID'] = df['Student_ID'].apply(anonymize_id)
print("  Student IDs anonymized.")

# DIMENSION TABLES

# dim_groups
dim_groups = df[['Group_ID']].drop_duplicates().reset_index(drop=True)
dim_groups.insert(0, 'Group_Key', range(1, len(dim_groups)+1))
dim_groups['Group_Type'] = dim_groups['Group_ID'].apply(
    lambda x: 'Robot-Assisted' if 'Robot' in x
              else ('Control' if 'Control' in x else 'Mixed'))

# dim_students
dim_students = df[['Anon_Student_ID', 'Group_ID']].drop_duplicates().reset_index(drop=True)
dim_students.insert(0, 'Student_Key', range(1, len(dim_students)+1))
dim_students = dim_students.rename(columns={'Anon_Student_ID': 'Student_ID'})

# dim_questions (70 pre-test + 70 post-test = 140 questions)
questions = []
q_key = 1
for q in range(1, 71):
    questions.append({'Question_Key': q_key, 'Question_Number': q,
                      'Test_Type': 'Pre-Test', 'Column_Name': f'Pre_Test_Q{q}'})
    q_key += 1
for q in range(1, 71):
    questions.append({'Question_Key': q_key, 'Question_Number': q,
                      'Test_Type': 'Post-Test', 'Column_Name': f'Post_Test_Q{q}'})
    q_key += 1
dim_questions = pd.DataFrame(questions)

# dim_assessment_items (32 pre-enjoy + 32 post-enjoy + 30 passion = 94 items)
items = []
item_key = 1
for phase, prefix, itype in [
    ('Pre',  'Pre_Enjoy_Item_',  'Enjoyment'),
    ('Post', 'Post_Enjoy_Item_', 'Enjoyment'),
    ('N/A',  'Passion_Item_',    'Passion'),
]:
    max_item = 32 if itype == 'Enjoyment' else 30
    for i in range(1, max_item + 1):
        items.append({'Item_Key': item_key, 'Item_Number': i,
                      'Item_Type': itype, 'Phase': phase,
                      'Column_Name': f'{prefix}{i}'})
        item_key += 1
dim_assessment_items = pd.DataFrame(items)

print(f"  dim_groups: {len(dim_groups)} rows")
print(f"  dim_students: {len(dim_students)} rows")
print(f"  dim_questions: {len(dim_questions)} rows")
print(f"  dim_assessment_items: {len(dim_assessment_items)} rows")

# FACT TABLES 
student_key_map = dict(zip(dim_students['Student_ID'], dim_students['Student_Key']))
group_key_map   = dict(zip(dim_groups['Group_ID'],     dim_groups['Group_Key']))

df['Anon_Student_Key'] = df['Anon_Student_ID'].map(student_key_map)
df['Group_Key']        = df['Group_ID'].map(group_key_map)

# fact_student_performance (main fact table — center of star)
fact_performance = df[['Anon_Student_Key', 'Group_Key',
                        'Total_Pre_Test', 'Total_Post_Test', 'Test_Knowledge_Gain',
                        'Total_Pre_Enjoyment', 'Total_Post_Enjoyment',
                        'Total_Passion', 'Passion_Learning_Efficiency']].copy()
fact_performance.insert(0, 'Fact_ID', range(1, len(fact_performance)+1))
fact_performance = fact_performance.rename(columns={'Anon_Student_Key': 'Student_Key'})

# fact_test_responses (one row per student per question)
print("  Building test responses table...")
test_response_rows = []
for _, row in df.iterrows():
    s_key = row['Anon_Student_Key']
    for qrow in dim_questions.itertuples():
        test_response_rows.append({
            'Student_Key':  s_key,
            'Question_Key': qrow.Question_Key,
            'Response':     int(row[qrow.Column_Name])
        })
fact_test_responses = pd.DataFrame(test_response_rows)
fact_test_responses.insert(0, 'Response_ID', range(1, len(fact_test_responses)+1))

# fact_assessment_responses (one row per student per item)
print("  Building assessment responses table...")
assess_rows = []
for _, row in df.iterrows():
    s_key = row['Anon_Student_Key']
    for arow in dim_assessment_items.itertuples():
        assess_rows.append({
            'Student_Key': s_key,
            'Item_Key':    arow.Item_Key,
            'Response':    int(row[arow.Column_Name])
        })
fact_assessment_responses = pd.DataFrame(assess_rows)
fact_assessment_responses.insert(0, 'Assessment_ID', range(1, len(fact_assessment_responses)+1))

print(f"  fact_student_performance: {len(fact_performance)} rows")
print(f"  fact_test_responses: {len(fact_test_responses):,} rows")
print(f"  fact_assessment_responses: {len(fact_assessment_responses):,} rows")

# SAVE CSVs 
print("\nSaving CSV files...")
dim_groups.to_csv(f'{OUTPUT_DIR}/dim_groups.csv', index=False)
dim_students.to_csv(f'{OUTPUT_DIR}/dim_students.csv', index=False)
dim_questions.to_csv(f'{OUTPUT_DIR}/dim_questions.csv', index=False)
dim_assessment_items.to_csv(f'{OUTPUT_DIR}/dim_assessment_items.csv', index=False)
fact_performance.to_csv(f'{OUTPUT_DIR}/fact_student_performance.csv', index=False)
fact_test_responses.to_csv(f'{OUTPUT_DIR}/fact_test_responses.csv', index=False)
fact_assessment_responses.to_csv(f'{OUTPUT_DIR}/fact_assessment_responses.csv', index=False)
print("  All CSV files saved.")

# LOAD INTO SQLITE DATABASE 
print("\nBuilding SQLite database...")
db_path = f'{OUTPUT_DIR}/{DB_NAME}'
conn = sqlite3.connect(db_path)
conn.executescript("""
PRAGMA foreign_keys = ON;
DROP TABLE IF EXISTS fact_assessment_responses;
DROP TABLE IF EXISTS fact_test_responses;
DROP TABLE IF EXISTS fact_student_performance;
DROP TABLE IF EXISTS dim_assessment_items;
DROP TABLE IF EXISTS dim_questions;
DROP TABLE IF EXISTS dim_students;
DROP TABLE IF EXISTS dim_groups;

CREATE TABLE dim_groups (
    Group_Key  INTEGER PRIMARY KEY,
    Group_ID   TEXT NOT NULL UNIQUE,
    Group_Type TEXT
);
CREATE TABLE dim_students (
    Student_Key INTEGER PRIMARY KEY,
    Student_ID  TEXT NOT NULL UNIQUE,
    Group_ID    TEXT,
    FOREIGN KEY (Group_ID) REFERENCES dim_groups(Group_ID)
);
CREATE TABLE dim_questions (
    Question_Key    INTEGER PRIMARY KEY,
    Question_Number INTEGER NOT NULL,
    Test_Type       TEXT NOT NULL,
    Column_Name     TEXT
);
CREATE TABLE dim_assessment_items (
    Item_Key    INTEGER PRIMARY KEY,
    Item_Number INTEGER NOT NULL,
    Item_Type   TEXT NOT NULL,
    Phase       TEXT,
    Column_Name TEXT
);
CREATE TABLE fact_student_performance (
    Fact_ID                     INTEGER PRIMARY KEY,
    Student_Key                 INTEGER NOT NULL,
    Group_Key                   INTEGER NOT NULL,
    Total_Pre_Test              INTEGER,
    Total_Post_Test             INTEGER,
    Test_Knowledge_Gain         INTEGER,
    Total_Pre_Enjoyment         INTEGER,
    Total_Post_Enjoyment        INTEGER,
    Total_Passion               INTEGER,
    Passion_Learning_Efficiency REAL,
    FOREIGN KEY (Student_Key) REFERENCES dim_students(Student_Key),
    FOREIGN KEY (Group_Key)   REFERENCES dim_groups(Group_Key)
);
CREATE TABLE fact_test_responses (
    Response_ID  INTEGER PRIMARY KEY,
    Student_Key  INTEGER NOT NULL,
    Question_Key INTEGER NOT NULL,
    Response     INTEGER,
    FOREIGN KEY (Student_Key)  REFERENCES dim_students(Student_Key),
    FOREIGN KEY (Question_Key) REFERENCES dim_questions(Question_Key)
);
CREATE TABLE fact_assessment_responses (
    Assessment_ID INTEGER PRIMARY KEY,
    Student_Key   INTEGER NOT NULL,
    Item_Key      INTEGER NOT NULL,
    Response      INTEGER,
    FOREIGN KEY (Student_Key) REFERENCES dim_students(Student_Key),
    FOREIGN KEY (Item_Key)    REFERENCES dim_assessment_items(Item_Key)
);
""")

dim_groups.to_sql('dim_groups', conn, if_exists='replace', index=False)
dim_students.to_sql('dim_students', conn, if_exists='replace', index=False)
dim_questions.to_sql('dim_questions', conn, if_exists='replace', index=False)
dim_assessment_items.to_sql('dim_assessment_items', conn, if_exists='replace', index=False)
fact_performance.to_sql('fact_student_performance', conn, if_exists='replace', index=False)
fact_test_responses.to_sql('fact_test_responses', conn, if_exists='replace', index=False)
fact_assessment_responses.to_sql('fact_assessment_responses', conn, if_exists='replace', index=False)
conn.commit()

# VERIFY WITH TEST QUERIES 
print("\nVerifying with SQL queries...")
q1 = pd.read_sql_query("""
    SELECT g.Group_ID, g.Group_Type,
           ROUND(AVG(f.Total_Post_Test), 2)      AS Avg_Post_Test,
           ROUND(AVG(f.Test_Knowledge_Gain), 2)  AS Avg_Gain,
           COUNT(*)                               AS Students
    FROM fact_student_performance f
    JOIN dim_groups g ON f.Group_Key = g.Group_Key
    GROUP BY g.Group_ID
""", conn)
print("\n[Group Performance Summary]")
print(q1.to_string(index=False))

conn.close()
print(f"\n✅ DONE! Database saved: {db_path}")
print(f"✅ Open with DB Browser for SQLite")
print(f"✅ Upload all files in '{OUTPUT_DIR}/' to GitHub")