# RESILIA MZ

Mini-rede solar **resiliente e eficiente** para Mabote (Inhambane, Moçambique).
Grupo 36 (UEM) · EMERGE Final Hackathon.

## O desafio e como respondemos

| Desafio | Onde está |
|---|---|
| Simulação que mostra como um sistema off-grid equilibra oferta e procura em **24 horas** | **Simulador 24 h**: balanço hora a hora de um dia real |
| Entradas: energia solar, capacidade da bateria, perfil de procura | Painel lateral: painéis (kWp), baterias (kWh), número de famílias e serviços |
| Saídas: balanço energético e risco de interrupção | Gráfico de 24 h, carga da bateria, energia em falta (%) e horas sem energia |
| Diferencial: optimizar para a **resiliência**, não só para a eficiência | **Dimensionamento**: 156 sistemas testados contra 11 anos de dias reais; o mais barato que aguenta os dias maus |

## Como funciona

1. **Dados reais:** sol e temperatura de Mabote, hora a hora, 2015–2025 (reanálise ERA5, Copernicus/ECMWF).
2. **Oferta:** só energia solar (painéis com efeito da temperatura). O sol varia hora a hora.
3. **Procura:** calculada a partir do número de famílias e dos serviços (centro de saúde, escola, bomba de água, moagem,
   iluminação pública). Varia com a hora, o dia da semana, o calor e de dia para dia.
4. **Balanço de cada hora:** sol → consumo; excedente → bateria; défice → bateria (até 20 % mínimo); o resto é
   energia em falta.
5. **Dimensionamento a longo prazo:** «só eficiência» = o mais barato para o dia médio; «resiliente» = o mais barato que
   cumpre o nível de protecção (energia em falta, dias maus por ano e autonomia) em 11 anos reais.

## Páginas

- **Apresentação** (página inicial, 6 diapositivos, cronómetro e notas do orador)
- **Energia solar** (o caminho da energia em 4 passos, indicadores de energia limpa, fluxo anual, sol ao longo do ano, glossário)
- **Simulador 24 h**
- **Dimensionamento**

A plataforma é bilingue (PT/EN): selector no canto superior direito ou `?lang=EN` no endereço.

## Executar

```bash
pip install -r requirements.txt
streamlit run app.py
```

Funciona offline com `data/MZ_era5.csv.gz`. Para reconstruir os dados: `python scripts/fetch_data.py`.

## Estrutura

| Ficheiro | Conteúdo |
|---|---|
| `app.py` | Navegação |
| `resilia/model.py` | Modelo: dados, oferta, procura, balanço horário e dimensionamento |
| `views/pitch.py` | Apresentação |
| `views/solar.py` | Energia solar (explicação e indicadores de energia renovável) |
| `views/simulator.py` | Simulador 24 h |
| `views/sizing.py` | Dimensionamento |
| `views/panel.py` | Painel lateral (aldeia e sistema) |
| `ui/` | Estilo, gráficos, ícones e idiomas |
