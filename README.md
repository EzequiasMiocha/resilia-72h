# RESILIA 72H

Gémeo digital de resiliência climática para mini-redes renováveis em Moçambique, Marrocos e Mali.
Projecto do Grupo 36 (UEM) para o EMERGE Final Hackathon.

## O que faz

- Recria as **72 horas mais duras** do clima real em cada local, com 11 anos de dados horários (ERA5 + poeira CAMS):
  ciclones Freddy, Dineo e Filipo (Mabote), neve e frio extremo (Imilchil, Alto Atlas), calor de 45 °C, poeira e
  chuvas torrenciais (Kayes).
- Simula cada componente com física própria: painéis (calor, poeira, neve, danos do vento), aerogerador (paragem de
  segurança), baterias LFP (limites térmicos do BMS), inversor (derating no calor), gerador e procura por prioridade.
- Compara, **com o mesmo equipamento**, a gestão convencional e a gestão RESILIA. A RESILIA usa o alerta
  meteorológico para pré-carregar, guarda uma reserva dinâmica para a clínica e faz cortes planeados por prioridade.
- Dimensiona o sistema mais barato que sobrevive ao pior evento real (e não ao dia médio), com CAPEX, LCOE e o valor
  da energia não servida.
- Funciona para **qualquer coordenada do planeta** e lê a **previsão real** dos próximos 4 dias (modo operacional).

## Idiomas / Languages

A plataforma é bilingue (Português / English). O selector PT/EN está sempre visível no canto superior direito e o
idioma fica guardado no endereço (`?lang=EN`), por isso pode partilhar-se um link já em inglês.

## Apresentação ao júri (7 minutos)

A página inicial é a **Apresentação**: 8 diapositivos só sobre Moçambique (Mabote, ciclone Freddy), com cronómetro,
tempo sugerido por diapositivo e notas do orador (interruptor «Notas do orador»). O diapositivo 5 mostra a simulação
real hora a hora, com 6 momentos-chave do ciclone e o «mapa de luzes».

## Executar

```bash
pip install -r requirements.txt
streamlit run app.py
```

A aplicação funciona offline com os dados em `data/`. Para reconstruir a base de dados a partir das fontes:

```bash
python scripts/fetch_data.py
```

## Estrutura

| Pasta / ficheiro | Conteúdo |
|---|---|
| `app.py` | Navegação (menu no topo) |
| `views/pitch.py` | Apresentação de 7 minutos |
| `views/controls.py` | Painel lateral das páginas de exploração |
| `resilia/sites.py` | Locais, eventos históricos e pressupostos de custo |
| `resilia/data.py` | Base de dados, detecção das janelas de 72 h, teste de stress, dados em directo |
| `resilia/physics.py` | Modelos físicos dos componentes |
| `resilia/loads.py` | Procura da comunidade por prioridade |
| `resilia/engine.py` | Despacho horário (convencional vs RESILIA) e indicadores |
| `resilia/optimize.py` | Dimensionamento robusto |
| `resilia/economics.py` | CAPEX, LCOE, valor da resiliência |
| `views/` | Um ficheiro por separador da interface |
| `ui/` | Estilo visual e gráficos |
| `data/` | Séries horárias 2015–2025 (ERA5/CAMS via Open-Meteo) |

## Fontes de dados

- Hersbach et al. (2020). The ERA5 global reanalysis. *QJRMS*. Copernicus Climate Change Service / ECMWF.
- CAMS — Copernicus Atmosphere Monitoring Service (poeira e aerossóis).
- Open-Meteo (Zippenfenig, 2023), APIs histórica, de qualidade do ar e de previsão.
