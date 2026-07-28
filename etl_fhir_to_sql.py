import gzip
import json
import os

import pandas as pd
from sqlalchemy import create_engine


def _database_engine():
    database_url = os.getenv("DEEPVITAL_DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "DEEPVITAL_DATABASE_URL is not configured. "
            "Copy .env.example to .env and provide a local database URL."
        )
    return create_engine(database_url)


def process_fhir_patients(file_path, engine=None):
    """Load only the minimum internal identifier needed for research grouping."""
    clean_patients = []
    print("Starting compressed FHIR data extraction...")
    
    # Read compressed NDJSON file
    with gzip.open(file_path, 'rt', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                resource = json.loads(line)
                
                # Extract patient ID
                patient_id = resource.get('id')
                
                # The internal identifier is retained for grouping only, never as a
                # predictor. Direct identifiers such as names are not extracted.
                gender = resource.get('gender', 'unknown')
                is_deceased = resource.get('deceasedBoolean', False)
                
                clean_patients.append({
                    'patient_id': patient_id,
                    'gender': gender,
                    'is_deceased': is_deceased
                })
                
    # Export DataFrame to SQL
    df_patients = pd.DataFrame(clean_patients)
    engine = engine or _database_engine()
    # Refuse to overwrite an existing table. This legacy loader must only target
    # an explicitly configured, disposable research database.
    df_patients.to_sql('patients', engine, if_exists='fail', index=False)
    print(f"Success! {len(df_patients)} patients saved to 'patients' table.")

if __name__ == "__main__":
    file_path = "data/mimic-iv-clinical-database-demo-on-fhir-2.1.0/fhir/MimicPatient.ndjson.gz" 
    process_fhir_patients(file_path)
