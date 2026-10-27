"""Locais piloto, eventos climáticos reais e pressupostos económicos.

Os eventos não têm datas “inventadas”: cada um tem uma janela de procura em torno do evento
histórico documentado e o motor escolhe, nos dados ERA5, as 72 h mais severas segundo o
critério físico do evento (menos sol, mais calor, mais neve, mais chuva).
"""

SITES = {
    "MZ": dict(
        name="Mabote", region="Província de Inhambane", country="Moçambique", flag="",
        lat=-22.05, lon=34.13, utc=2, dust=False,
        households=200, people=1400,
        hazard="Ciclones tropicais, cheias e chuvas torrenciais",
        context=("Distrito rural do interior de Inhambane, a ~100 km da costa de Vilankulo. "
                 "A rede nacional não chega à maioria das aldeias; o corredor costeiro de Inhambane "
                 "é uma das zonas de entrada de ciclones mais frequentes de Moçambique."),
        met_service="INAM (Instituto Nacional de Meteorologia)",
        disaster_agency="INGD (Gestão e Redução do Risco de Desastres)",
        energy_agency="FUNAE / ALER / EDM",
        diesel_usd_l=1.35, tariff_usd_kwh=0.30, currency="MZN",
        default_event="freddy",
        default_sys=dict(pv=45, bat=120, inv=25),
        heat_sens=0.6, cold_sens=0.0,
        water_head_m=45,
    ),
    "MA": dict(
        name="Imilchil", region="Alto Atlas (província de Midelt)", country="Marrocos", flag="",
        lat=32.15, lon=-5.63, utc=1, dust=True,
        households=120, people=850,
        hazard="Neve, frio extremo e isolamento de aldeias de montanha",
        context=("Aldeias de montanha a ~2 200 m de altitude. O acesso à electricidade em Marrocos é "
                 "quase universal, mas as aldeias de montanha ficam isoladas por neve e sismos "
                 "(Al Haouz, 2023): o desafio aqui é manter serviços críticos quando as estradas fecham."),
        met_service="DGM — Direction Générale de la Météorologie",
        disaster_agency="Protection Civile / Ministère de l'Intérieur",
        energy_agency="ONEE / MASEN / IRESEN",
        diesel_usd_l=1.30, tariff_usd_kwh=0.25, currency="MAD",
        default_event="neve2025",
        default_sys=dict(pv=35, bat=100, inv=20),
        heat_sens=0.2, cold_sens=1.0,
        water_head_m=60,
    ),
    "ML": dict(
        name="Kayes (aldeia rural)", region="Região de Kayes", country="Mali", flag="",
        lat=14.45, lon=-11.44, utc=0, dust=True,
        households=220, people=1700,
        hazard="Calor extremo, tempestades de poeira e chuvas torrenciais",
        context=("Kayes é uma das cidades mais quentes de África. Em Abril de 2024 uma onda de calor "
                 "histórica atingiu o Mali com temperaturas acima de 45 °C, em plena crise de cortes "
                 "de electricidade — exactamente quando clínicas e água precisavam mais de energia."),
        met_service="Mali-Météo (Agence Nationale de la Météorologie)",
        disaster_agency="Direction Générale de la Protection Civile",
        energy_agency="AMADER / AER-Mali",
        diesel_usd_l=1.25, tariff_usd_kwh=0.28, currency="XOF",
        default_event="calor2024",
        default_sys=dict(pv=55, bat=150, inv=30),
        heat_sens=1.0, cold_sens=0.0,
        water_head_m=55,
    ),
}

# criterio: min_solar | max_heat | max_snow | max_rain | min_temp
EVENTS = {
    # ── Moçambique ──
    "freddy": dict(site="MZ", name="Ciclone Freddy (Fev 2023)", kind="ciclone",
                   search=("2023-02-23", "2023-03-01"), rule="min_solar", start="2023-02-24 12:00",
                   story=("O Freddy foi o ciclone tropical de maior duração alguma vez registado (mais de "
                          "5 semanas). Entrou em Moçambique a 24 de Fevereiro de 2023 a norte de Vilankulo, "
                          "Inhambane. Em Mabote, os dados mostram a pressão a cair para 995 hPa, rajadas de "
                          "~30 m/s, chuva forte e quase 4 dias de céu totalmente encoberto.")),
    "dineo": dict(site="MZ", name="Ciclone Dineo (Fev 2017)", kind="ciclone",
                  search=("2017-02-14", "2017-02-20"), rule="min_solar",
                  story=("O Dineo atingiu a costa de Inhambane a 15 de Fevereiro de 2017. Em Mabote: mais de "
                         "100 mm de chuva num dia, rajadas acima de 20 m/s e um dia quase sem sol.")),
    "filipo": dict(site="MZ", name="Tempestade tropical Filipo (Mar 2024)", kind="ciclone",
                   search=("2024-03-10", "2024-03-15"), rule="min_solar",
                   story=("O Filipo entrou pela província de Inhambane em Março de 2024. Evento curto mas "
                          "intenso: ~96 mm de chuva num dia, pressão a 997 hPa e rajadas de 25 m/s.")),
    # ── Marrocos ──
    "neve2025": dict(site="MA", name="Tempestade de neve (Dez 2025)", kind="neve",
                     search=("2025-12-12", "2025-12-20"), rule="max_snow",
                     story=("Episódio de inverno no Alto Atlas: mais de 30 cm de neve acumulada em 72 h, "
                            "temperaturas até −10 °C e céu encoberto. Painéis cobertos de neve, baterias de lítio "
                            "que não aceitam carga abaixo de 0 °C e estradas de montanha fechadas.")),
    "frio2021": dict(site="MA", name="Vaga de frio (Jan 2021)", kind="frio",
                     search=("2021-01-08", "2021-01-20"), rule="min_temp",
                     story=("As 72 h mais frias da última década em Imilchil (média abaixo de −7 °C). "
                            "O sol existe, mas as baterias geladas não conseguem carregar.")),
    "nov2019": dict(site="MA", name="Tempestade de Novembro (2019)", kind="tempestade",
                    search=("2019-11-19", "2019-11-26"), rule="min_solar",
                    story=("A janela de 72 h com menos sol de toda a série 2015–2025 em Imilchil: "
                           "nuvens persistentes, chuva e neve fraca.")),
    # ── Mali ──
    "calor2024": dict(site="ML", name="Onda de calor + poeira (Abr 2024)", kind="calor",
                      search=("2024-03-29", "2024-04-09"), rule="max_heat",
                      story=("A onda de calor de Abril de 2024 no Sahel. Na região de Kayes há máximas de 45 °C "
                             "e noites acima de 30 °C, com poeira em suspensão. O calor reduz a produção dos "
                             "painéis e obriga inversores e baterias a reduzir potência, ao mesmo tempo que "
                             "dispara a procura nas clínicas, na água e no frio.")),
    "calor2023": dict(site="ML", name="Calor extremo (Mai 2023)", kind="calor",
                      search=("2023-05-25", "2023-06-04"), rule="max_heat",
                      story=("As 72 h mais quentes de 2023 em Kayes, no pico da estação seca, com dados "
                             "reais de poeira (CAMS).")),
    "chuva2021": dict(site="ML", name="Chuvas torrenciais (Ago 2021)", kind="cheia",
                      search=("2021-08-14", "2021-08-23"), rule="max_rain",
                      story=("A janela de 72 h mais chuvosa da década na região de Kayes (~118 mm): estradas "
                             "de terra intransitáveis, céu encoberto e risco de cheia.")),
}

# Custos indicativos (USD, mini-redes em África, 2024-2025). Fontes de ordem de grandeza:
# ESMAP (2022) Mini Grids for Half a Billion People; IRENA (2024) Renewable Power Generation Costs;
# BNEF (2024) Battery Price Survey. Todos editáveis na aba de negócio.
COSTS = dict(
    pv_usd_kwp=650.0,            # módulos + estrutura + BOS DC + inversor PV
    pv_hardening_usd_kwp=120.0,  # estrutura anti-ciclone (ancoragem, perfis reforçados)
    bat_usd_kwh=320.0,           # LFP instalado (BMS, armário)
    bat_climate_fixed=6000.0,    # contentor isolado/climatizado
    bat_climate_usd_kwh=15.0,
    inv_usd_kw=250.0,            # inversor/carregador de bateria
    wind_usd_kw=3500.0,          # aerogerador pequeno instalado (torre incluída)
    diesel_usd_kw=450.0,
    smart_fixed=5000.0,          # controlador RESILIA + relés por alimentador + ligação a alertas
    smart_usd_household=45.0,    # contador inteligente com limitação de potência
    soft_costs=0.15,             # engenharia, logística, licenças
    om_frac=0.02,                # O&M anual (% do CAPEX)
    bat_life_y=12, project_life_y=20, discount=0.10,
)

# Valor da energia não servida (USD/kWh) — pressuposto explícito, editável
VOLL = dict(critica=10.0, essencial=2.0, produtiva=1.0)

CO2_KG_PER_L = 2.68

# ───────────── versões em inglês (interface bilingue) ─────────────
SITES_EN = {
    "MZ": dict(name="Mabote", region="Inhambane Province", country="Mozambique",
               hazard="Tropical cyclones, floods and torrential rain",
               context=("Rural district in inland Inhambane, ~100 km from the Vilankulo coast. The national grid "
                        "does not reach most villages; the Inhambane coastline is one of Mozambique's most frequent "
                        "cyclone landfall corridors.")),
    "MA": dict(name="Imilchil", region="High Atlas (Midelt Province)", country="Morocco",
               hazard="Snow, extreme cold and isolation of mountain villages",
               context=("Mountain villages at ~2,200 m altitude. Electricity access in Morocco is almost universal, "
                        "but mountain villages are cut off by snow and earthquakes (Al Haouz, 2023): the challenge is "
                        "keeping critical services running when roads close.")),
    "ML": dict(name="Kayes (rural village)", region="Kayes Region", country="Mali",
               hazard="Extreme heat, dust storms and torrential rain",
               context=("Kayes is one of the hottest cities in Africa. In April 2024 a historic heatwave hit Mali with "
                        "temperatures above 45 °C, in the middle of a power-cut crisis — exactly when clinics and "
                        "water needed energy most.")),
}

EVENTS_EN = {
    "freddy": dict(name="Cyclone Freddy (Feb 2023)",
                   story=("Freddy was the longest-lived tropical cyclone ever recorded (more than 5 weeks). It made "
                          "landfall in Mozambique on 24 February 2023 north of Vilankulo, Inhambane. In Mabote, the data "
                          "show pressure dropping to 995 hPa, gusts of ~30 m/s, heavy rain and almost 4 days of fully "
                          "overcast sky.")),
    "dineo": dict(name="Cyclone Dineo (Feb 2017)",
                  story=("Dineo hit the Inhambane coast on 15 February 2017. In Mabote: more than 100 mm of rain in one "
                         "day, gusts above 20 m/s and a day with almost no sun.")),
    "filipo": dict(name="Tropical storm Filipo (Mar 2024)",
                   story=("Filipo entered through Inhambane Province in March 2024. Short but intense: ~96 mm of rain "
                          "in one day, pressure at 997 hPa and gusts of 25 m/s.")),
    "neve2025": dict(name="Snowstorm (Dec 2025)",
                     story=("Winter episode in the High Atlas: more than 30 cm of snow in 72 h, temperatures down to "
                            "−10 °C and overcast sky. Panels covered in snow, lithium batteries that cannot charge below "
                            "0 °C and mountain roads closed.")),
    "frio2021": dict(name="Cold wave (Jan 2021)",
                     story=("The coldest 72 h of the decade in Imilchil (average below −7 °C). The sun is there, but "
                            "frozen batteries cannot charge.")),
    "nov2019": dict(name="November storm (2019)",
                    story=("The 72-hour window with the least sunshine of the whole 2015–2025 series in Imilchil: "
                           "persistent clouds, rain and light snow.")),
    "calor2024": dict(name="Heatwave + dust (Apr 2024)",
                      story=("The April 2024 Sahel heatwave. In the Kayes region, highs of 45 °C and nights above 30 °C, "
                             "with dust in the air. Heat cuts panel output and forces inverters and batteries to derate, "
                             "while demand at clinics, for water and for cooling soars.")),
    "calor2023": dict(name="Extreme heat (May 2023)",
                      story="The hottest 72 h of 2023 in Kayes, at the peak of the dry season, with real dust data (CAMS)."),
    "chuva2021": dict(name="Torrential rain (Aug 2021)",
                      story=("The wettest 72-hour window of the decade in the Kayes region (~118 mm): dirt roads "
                             "impassable, overcast sky and flood risk.")),
}
