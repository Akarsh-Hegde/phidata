import pandas as pd

df = pd.read_excel('/Users/akarshhegde/Downloads/1.Faculty Appraisal (Jan - Dec 2023) (Responses).xlsx')

df.to_parquet('1.Faculty Appraisal (Jan - Dec 2023) (Responses).parquet', engine='fastparquet')