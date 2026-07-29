# JOYA Enterprise 5.4 — API Market Discovery + Cartillas Globales DEV

Esta versión aplica la regla:

> API-Football determina qué mercados existen. JOYA determina cuáles merecen seleccionarse.

## Funciones principales

### API Market Discovery
- Consulta mercados y cuotas disponibles por partido.
- Normaliza nombres de mercado.
- Guarda bookmaker, línea, selección y cuota.
- Omite mercados que no están disponibles en la API.

### Proyección JOYA
Cada mercado descubierto se cruza con:
- Data Quality.
- Forma reciente.
- Local/visita.
- H2H opcional.
- Projection Engine.
- JOYA Score.
- Riesgo.
- Probabilidad implícita.
- Edge estimado.

### Cartillas automáticas
- Núcleo Sangrado.
- Top Ranking del Día.
- Elite.
- S+++.
- S++.
- S+.
- Soñadora.
- Escalera.

## Streamlit

Ejecuta:

```bash
pip install -r requirements.txt
streamlit run app.py
```

En Secrets:

```toml
API_FOOTBALL_KEY = "TU_API_KEY"
```

## Nota de consumo API

La búsqueda global de cuotas puede consumir muchas solicitudes.
La interfaz permite limitar:
- partidos analizados;
- bookmakers;
- mercados por partido;
- League Score mínimo.
