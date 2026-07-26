import json
import gzip
import pandas as pd
from sqlalchemy import create_engine

# Connect to local PostgreSQL
engine = create_engine('postgresql://deepvital_admin:admin_password@localhost:5432/uci_data')

def process_vital_signs(file_path):
    records = []
    print("Starting vital signs extraction (Chartevents)...")
    
    # Read compressed NDJSON file
    with gzip.open(file_path, 'rt', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                resource = json.loads(line)
                
                # Extract patient reference (e.g., "Patient/12345" -> "12345")
                subject_ref = resource.get('subject', {}).get('reference', '')
                patient_id = subject_ref.split('/')[-1] if '/' in subject_ref else subject_ref
                
                # Extract exact timestamp
                timestamp = resource.get('effectiveDateTime')
                
                # Extract numerical value and unit
                value = None
                unit = None
                if 'valueQuantity' in resource:
                    value = resource['valueQuantity'].get('value')
                    unit = resource['valueQuantity'].get('unit')
                
                # Extract sensor code
                sensor_code = None
                if 'code' in resource and 'coding' in resource['code']:
                    sensor_code = resource['code']['coding'][0].get('code')
                
                # Save only complete records
                if patient_id and timestamp and value is not None:
                    records.append({
                        'patient_id': patient_id,
                        'timestamp': timestamp,
                        'sensor_code': sensor_code,
                        'value': value,
                        'unit': unit
                    })
                    
    # Convert to DataFrame
    df_vitals = pd.DataFrame(records)
    
    # Convert column to Datetime format with UTC
    df_vitals['timestamp'] = pd.to_datetime(df_vitals['timestamp'], utc=True)
    
    # Save to PostgreSQL
    df_vitals.to_sql('vital_signs', engine, if_exists='replace', index=False)
    print(f"Success! {len(df_vitals)} records saved to 'vital_signs' table.")

if __name__ == "__main__":
    file_path = "data/mimic-iv-clinical-database-demo-on-fhir-2.1.0/fhir/MimicObservationChartevents.ndjson.gz"
    process_vital_signs(file_path)