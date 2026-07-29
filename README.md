# JOYA Enterprise 4.4.0 DEV

Release sincronizada del Sprint:

1. API Manager
2. Scanner por fecha
3. Match Center
4. Data Quality Engine
5. Projection Engine
6. Winner Engine
7. JOYA Score

## Instalación

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Secret de Streamlit

Crea `.streamlit/secrets.toml`:

```toml
API_FOOTBALL_KEY = "TU_API_KEY"
```

También acepta la variable de entorno `API_FOOTBALL_KEY`.

## Principios

- La API entrega datos; JOYA entrega decisiones.
- Ningún mercado se aprueba si Data Quality no supera el umbral.
- Las proyecciones no son picks automáticos.
- Ante información insuficiente: NO BET.
- El Winner Engine no llama directamente a la API.
