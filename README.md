# JOYA Enterprise 5.0 — Sprint 1 DEV

Primera base de JOYA Enterprise 5.0.

## Incluye

- Data Hub tolerante a fallos.
- Intelligence Hub.
- Team Analyzer.
- League Analyzer.
- Projection Engine 3.0.
- Winner y Goal Engines heredados.
- JOYA Score 4.0.
- Learning Engine con SQLite.
- Historial de análisis y resultados.
- Dashboard de precisión.

## Importante

Esta versión no pretende afirmar que “aprende sola” de forma mágica.
El Learning Engine guarda resultados y calcula métricas para permitir una
calibración posterior basada en evidencia.

## Ejecución

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Streamlit Secrets

```toml
API_FOOTBALL_KEY = "TU_API_KEY"
```

La base local se crea automáticamente en:

```text
data/joya_learning.db
```
