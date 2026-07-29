# JOYA Enterprise 4.6.0 DEV

Esta versión incorpora **Projection Engine 2.0**.

## Qué corrige

La versión anterior podía interpretar una respuesta vacía de la API como
`0.00 goles esperados`, produciendo unders al 100%. En esta versión:

1. Se valida la proyección de la API.
2. Se consultan los últimos 10 partidos de ambos equipos.
3. Se calcula rendimiento general y local/visita.
4. Se consulta H2H reciente.
5. Se crea una proyección estadística conservadora.
6. Si la información aún no es suficiente, los mercados de goles quedan en NO BET.

## Flujo

API-Football
→ Data Quality
→ Team Form
→ Home/Away Split
→ H2H
→ Projection Engine 2.0
→ Decision Engines
→ Ranking diversificado

## Configuración

```toml
API_FOOTBALL_KEY = "TU_API_KEY"
```

## Ejecución

```bash
pip install -r requirements.txt
streamlit run app.py
```
