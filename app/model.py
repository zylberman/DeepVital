import torch
from torch import nn


# 1. Definición de la Arquitectura de la Red Neuronal
class DeepVitalModel(nn.Module):
    def __init__(self):
        super().__init__()
        
        # Brazo 1: Procesa los datos estáticos (Ej: Edad, Peso, Género codificado)
        # Suponemos que entran 5 variables clínicas estáticas
        self.tabular_branch = nn.Sequential(
            nn.Linear(5, 16),
            nn.ReLU(),
            nn.Linear(16, 8)
        )
        
        # Brazo 2: Procesa la serie temporal del sensor (Ej: Frecuencia cardíaca de las últimas 12h)
        # Usamos una capa LSTM (Long Short-Term Memory) ideal para secuencias temporales
        self.sensor_branch = nn.LSTM(input_size=1, hidden_size=16, num_layers=1, batch_first=True)
        
        # Fusión: Une la información clínica con los patrones del sensor para dar el diagnóstico
        # Recibe los 8 nodos del brazo tabular + los 16 nodos del brazo del sensor
        self.fusion_layer = nn.Sequential(
            nn.Linear(8 + 16, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
            nn.Sigmoid() # Devuelve una probabilidad clínica entre 0 y 1 (Ej: 0.85 = 85% de riesgo)
        )

    def forward(self, datos_tabulares, datos_sensores):
        # Pasar datos por el brazo tabular
        out_tab = self.tabular_branch(datos_tabulares)
        
        # Pasar datos por el brazo del sensor
        out_sensor, _ = self.sensor_branch(datos_sensores)
        # Solo nos quedamos con la última predicción de la secuencia de tiempo
        out_sensor = out_sensor[:, -1, :] 
        
        # Fusionar ambos resultados (concatenación)
        fusion = torch.cat((out_tab, out_sensor), dim=1)
        
        # Predicción final
        resultado_final = self.fusion_layer(fusion)
        return resultado_final

# 2. Bloque de Ejecución y Prueba (Dummy Data)
if __name__ == "__main__":
    print("Inicializando el modelo DeepVital en PyTorch...")
    modelo = DeepVitalModel()
    
    # Simulemos un "Lote" (Batch) de 4 pacientes para probar que la red funciona
    
    # 4 pacientes x 5 variables clínicas (Edad normalizada, etc.)
    pacientes_tabulares = torch.rand(4, 5) 
    
    # 4 pacientes x 12 mediciones de tiempo (12 horas) x 1 sensor (Frecuencia Cardíaca)
    pacientes_sensores = torch.rand(4, 12, 1) 
    
    print("\nAlimentando la red neuronal con los datos de los 4 pacientes...")
    
    # Ejecutamos la predicción (Forward pass)
    prediccion_riesgo = modelo(pacientes_tabulares, pacientes_sensores)
    
    print("\n--- RESULTADOS DEL PRONÓSTICO ---")
    for i, riesgo in enumerate(prediccion_riesgo):
        porcentaje = riesgo.item() * 100
        alerta = "¡ALERTA CRÍTICA!" if porcentaje > 75 else "Estable"
        print(f"Paciente {i+1} | Probabilidad de evento adverso: {porcentaje:.2f}% -> {alerta}")
