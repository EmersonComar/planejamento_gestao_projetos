import streamlit as st
import os
from src.domain.entities import DengueRiskInput
from src.infrastructure.ml.predictor import SklearnPredictor
from src.application.use_cases.predict_risk import PredictRiskUseCase

st.set_page_config(page_title="Predicao de Risco de Dengue", layout="wide")

@st.cache_resource
def get_use_case():
    model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models", "modelo_baseline_risco_dengue.pkl")
    predictor = SklearnPredictor(model_path)
    return PredictRiskUseCase(predictor)

def main():
    st.title("Sistema de Classificacao de Risco de Dengue")
    
    use_case = get_use_case()
    
    with st.form("predict_form"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            temperatura = st.number_input("Temperatura Media (C)", value=25.0)
            umidade = st.number_input("Umidade Media (%)", value=70.0)
            precipitacao = st.number_input("Precipitacao Total (mm)", value=100.0)
            
        with col2:
            densidade = st.number_input("Densidade Demografica", value=100.0)
            mes = st.selectbox("Mes", options=list(range(1, 13)))
            
        with col3:
            casos_lag1 = st.number_input("Casos (Mes Anterior)", min_value=0.0, value=0.0)
            incidencia_lag1 = st.number_input("Incidencia (Mes Anterior)", min_value=0.0, value=0.0)
            
        submitted = st.form_submit_button("Analisar Risco")
        
    if submitted:
        input_data = DengueRiskInput(
            temperatura_media=temperatura,
            umidade_media=umidade,
            precipitacao_total=precipitacao,
            densidade_demografica=densidade,
            mes=mes,
            casos_lag1=casos_lag1,
            incidencia_lag1=incidencia_lag1
        )
        
        try:
            result = use_case.execute(input_data)
            
            st.subheader("Resultado da Analise")
            
            if result.risk_level.name == "HIGH":
                st.error(f"Risco: {result.risk_level.value} (Probabilidade: {result.probability:.2%})")
            else:
                st.success(f"Risco: {result.risk_level.value} (Probabilidade: {result.probability:.2%})")
                
        except Exception as e:
            st.error(f"Erro ao processar predicao: {str(e)}")

if __name__ == "__main__":
    main()
