# JOYA Enterprise 5.1 — Corner Engine PRO DEV

Primera entrega funcional de los motores especializados.

## Corner Engine PRO

Analiza estadísticas reales de los partidos recientes de ambos equipos:

- Córners a favor.
- Córners en contra.
- Córners totales.
- Rendimiento local y visitante.
- Calidad de muestra.
- Volatilidad.
- Proyección central.

## Mercados

- Más/Menos de 7.5 córners.
- Más/Menos de 8.5 córners.
- Más/Menos de 9.5 córners.
- Más/Menos de 10.5 córners.
- Más/Menos de 11.5 córners.
- Local más de 3.5 / 4.5 / 5.5 córners.
- Visitante más de 2.5 / 3.5 / 4.5 córners.
- Equipo con más córners.
- Rango 7–13 y 8–12 córners.

Cuando la muestra no es suficiente, el motor responde NO BET.

## Consumo de API

El análisis consulta estadísticas de hasta 8 partidos recientes por equipo.
Las respuestas se guardan en caché durante 30 minutos.

## Ejecución

```bash
pip install -r requirements.txt
streamlit run app.py
```

Configura en Streamlit Secrets:

```toml
API_FOOTBALL_KEY = "TU_API_KEY"
```
