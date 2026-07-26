import json
import gzip
import pandas as pd
from sqlalchemy import create_engine

# Connect to local PostgreSQL
engine = create_engine('postgresql://deepvital_admin:admin_password@localhost:5432/uci_data')

def process_fhir_patients(file_path):
    clean_patients = []
    print("Starting compressed FHIR data extraction...")
    
    # Read compressed NDJSON file
    with gzip.open(file_path, 'rt', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                resource = json.loads(line)
                
                # Extract patient ID
                patient_id = resource.get('id')
                
                # Extract full name
                full_name = "Unknown"
                if resource.get('name'):
                    last_name = resource['name'][0].get('family', '')
                    first_names = resource['name'][0].get('given', [''])
                    first_name = first_names[0] if first_names else ''
                    full_name = f"{first_name} {last_name}".strip()
                
                # Extract demographics
                gender = resource.get('gender', 'unknown')
                birth_date = resource.get('birthDate')
                is_deceased = resource.get('deceasedBoolean', False)
                
                clean_patients.append({
                    'patient_id': patient_id,
                    'full_name': full_name,
                    'gender': gender,
                    'birth_date': birth_date,
                    'is_deceased': is_deceased
                })
                
    # Export DataFrame to SQL
    df_patients = pd.DataFrame(clean_patients)
    df_patients.to_sql('patients', engine, if_exists='replace', index=False)
    print(f"Success! {len(df_patients)} patients saved to 'patients' table.")

if __name__ == "__main__":
    file_path = "data/mimic-iv-clinical-database-demo-on-fhir-2.1.0/fhir/MimicPatient.ndjson.gz" 
    process_fhir_patients(file_path)