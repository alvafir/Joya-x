import pandas as pd

def build_match_table(fixtures):
    rows=[]
    for item in fixtures:
        league=item.get("league",{})
        teams=item.get("teams",{})
        fixture=item.get("fixture",{})
        rows.append({
            "País":league.get("country",""),
            "Liga":league.get("name",""),
            "Hora":str(fixture.get("date",""))[:16].replace("T"," "),
            "Local":teams.get("home",{}).get("name",""),
            "Visitante":teams.get("away",{}).get("name",""),
            "Fixture ID":fixture.get("id","")
        })
    return pd.DataFrame(rows)
