import os
from streamlit.testing.v1 import AppTest

def test_app_loads_and_predicts():
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "app", "main.py")
    at = AppTest.from_file(script_path).run()
    
    assert not at.exception
    assert at.title[0].value == "Sistema de Classificacao de Risco de Dengue"
    
    at.number_input[0].set_value(30.0)
    
    at.button[0].click().run()
    
    assert not at.exception
    assert len(at.subheader) > 0
    assert at.subheader[0].value == "Resultado da Analise"
