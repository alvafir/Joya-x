# JOYA Enterprise 4.5.0 DEV

Versión ampliada con arquitectura multi-motor:

- Data Quality Engine
- Projection Engine
- Winner Engine
- Goal Engine
- Corner Engine
- Card Engine
- Shot Engine
- Market Orchestrator
- JOYA Score 2.0
- Ranking global TOP 10

## Mercados incluidos

### Winner
1X2, doble oportunidad, DNB, gana cualquier mitad, ganador 1T y doble oportunidad 1T.

### Goals
Over/Under FT, Over/Under 1T, BTTS, goles por equipo, rango de goles,
sin gol antes del 10/20, gol antes del 60/70/80 y equipo marca primero.

### Corner / Cards / Shots
La arquitectura está activa. Cuando la API no entrega estadísticas suficientes,
el sistema devuelve NO BET en vez de inventar probabilidades.

## Ejecución

```bash
pip install -r requirements.txt
streamlit run app.py
```

Configura:

```toml
API_FOOTBALL_KEY = "TU_API_KEY"
```

en Streamlit Secrets.
