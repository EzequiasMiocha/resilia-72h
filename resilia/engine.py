"""Motor de despacho horário: estratégia convencional vs estratégia RESILIA.

Convencional (o que existe hoje na maioria das mini-redes):
  • um único alimentador — quando a energia não chega para tudo, cai tudo (inclui a clínica);
  • o inversor desliga a bateria ao chegar ao mínimo e só religa aos 30 % (protecção LVD);
  • gerador (se existir) só arranca quando a bateria está baixa; sem previsão meteorológica.

RESILIA (inteligente e orientada a resiliência):
  • recebe o alerta meteorológico com X horas de antecedência (INAM / DGM / Mali-Météo);
  • pré-carrega a bateria e enche o depósito de água antes do evento;
  • reserva dinâmica: guarda na bateria a energia que as cargas críticas vão precisar até ao fim do
    evento (descontando metade do sol previsto);
  • alimentadores separados por prioridade + contadores inteligentes: corta primeiro a moagem, depois
    limita as casas ao “modo essencial” (luz + telemóvel) e só em último caso toca na clínica;
  • raciona o gasóleo (estradas cortadas = sem reabastecimento) para o que é crítico;
  • manutenção activa: limpeza de neve e de poeira dos painéis por técnico local.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .loads import Community, build_demand, severe_flags
from .physics import Resource, System, diesel_fuel, resource, snow_and_soiling
from .sites import CO2_KG_PER_L

ETA_C = ETA_D = 0.96
SOC_MIN = 0.10
C_RATE = 0.5


@dataclass
class Strategy:
    smart: bool = True
    lead_h: int = 48          # antecedência do alerta meteorológico (h)
    maint: bool = True        # limpeza de neve/poeira
    name: str = "RESILIA"


CONVENTIONAL = Strategy(smart=False, lead_h=0, maint=False, name="Convencional")
RESILIA = Strategy(smart=True, lead_h=48, maint=True, name="RESILIA")


def _event_geometry(ev: np.ndarray, lead: int):
    """alert[t]: há evento entre t e t+lead; nxt[t]: próxima hora de evento; end[t]: fim do evento."""
    n = len(ev)
    nxt = np.full(n + 1, 10 ** 9)
    for t in range(n - 1, -1, -1):
        nxt[t] = t if ev[t] else nxt[t + 1]
    nxt = nxt[:n]
    alert = (nxt - np.arange(n)) <= lead if lead >= 0 else np.zeros(n, bool)
    end = np.full(n, -1)
    last = -1
    for t in range(n - 1, -1, -1):
        if ev[t] and (t == n - 1 or not ev[t + 1]):
            last = t
        end[t] = last
    return alert, nxt, end


def _gen_power(target: float, rated: float, fuel: float) -> float:
    """Potência do gerador: carga mínima 30 %, limitada à potência nominal e ao gasóleo."""
    if rated <= 0 or fuel <= 0.5 or target <= 1e-9:
        return 0.0
    g = min(rated, max(target, 0.3 * rated))
    return max(0.0, min(g, (fuel - 0.08415 * rated) / 0.246))


def simulate(w: pd.DataFrame, site: dict, sys: System, comm: Community, strat: Strategy,
             intensity: float = 1.0, fuel_resupply: bool = False, soc0: float = 0.6,
             tank0: float = 0.5, res: Resource | None = None, ss=None, dem=None) -> pd.DataFrame:
    n = len(w)
    has_phase = "fase" in w
    phase = w["fase"].values if has_phase else np.array(["normal"] * n, dtype=object)
    sev = severe_flags(w)
    ev = (phase == "evento") if has_phase else sev
    if dem is None:
        dem = build_demand(w, comm, sev | ev)
    if res is None:
        res = resource(w, site, sys, intensity)
    if ss is None:
        ss = snow_and_soiling(w, res.poa, res.extras["tilt"], strat.smart and strat.maint)
    snow, soil = ss
    pv = res.pv_base * (1 - snow) * (1 - soil) * (1 - res.damage)
    turb_dead = np.maximum.accumulate(res.gust_hub * intensity >= 52)   # sobrevivência do aerogerador
    wind = np.where(turb_dead, 0.0, res.wind)

    alert, nxt, ev_end = _event_geometry(ev, strat.lead_h if strat.smart else -1)
    crit_all = dem.crit + res.aux
    Sc = np.concatenate([[0], np.cumsum(crit_all)])
    # necessidade líquida prevista, hora a hora: o que o sol previsto não cobre directamente.
    # Prudência ajustada à confiança da previsão: céu limpo → 85 % do sol previsto; céu encoberto → 50 %.
    cc = w["cloud_cover"].values if "cloud_cover" in w else np.full(n, 50.0)
    conf = np.clip(0.85 - 0.35 * (cc - 30) / 40, 0.5, 0.85)
    pv_fc = conf * pv
    Sc = np.concatenate([[0], np.cumsum(np.maximum(crit_all - pv_fc, 0))])
    Sm = np.concatenate([[0], np.cumsum(np.maximum(crit_all + dem.ess_min - pv_fc, 0))])
    Sa = np.concatenate([[0], np.cumsum(np.maximum(crit_all + dem.ess_full + dem.prod - pv_fc, 0))])

    def _net(load):
        """Fluxo líquido previsto para a bateria (+ défice a descarregar, − excedente que recarrega)."""
        x = load - pv_fc
        return np.where(x > 0, x / ETA_D, x * ETA_C)

    net_c, net_m = _net(crit_all), _net(crit_all + dem.ess_min)
    net_a = _net(crit_all + dem.ess_full + dem.prod)

    def need(net, a, b):
        """Energia que a bateria tem de ter agora para não falhar até b (máximo défice acumulado,
        contando com as recargas solares pelo caminho) — o método clássico de dimensionar armazenamento."""
        if b <= a:
            return 0.0
        return max(0.0, float(np.cumsum(net[a:b]).max()))

    L = lambda a: [float(x) for x in a]
    pv_, wind_, crit_, essf_, essm_, prod_ = L(pv), L(wind), L(crit_all), L(dem.ess_full), L(dem.ess_min), L(dem.prod)
    water_ = L(dem.water_m3)
    chg_, dis_, capf_, invf_ = L(res.chg_f), L(res.dis_f), L(res.cap_f), L(res.inv_f)
    hours = w.index.hour.values

    has_bat = sys.bat_kwh > 0
    cap = max(sys.bat_kwh, 1e-6)
    E = soc0 * sys.bat_kwh
    fuel_cap = sys.fuel_l
    fuel = fuel0 = fuel_cap * sys.fuel_init
    tank_cap = dem.tank_m3; tank = tank0 * tank_cap
    kwh_m3, pump_kw = dem.kwh_m3, dem.pump_kw
    rated = sys.diesel_kw if fuel_cap > 0 else 0.0
    lockout = False
    fuel_used_pre = 0.0
    fuel_burn = 0.0

    keys = ["pv_av", "pv", "wind", "bat_dis", "bat_ch", "diesel", "fuel", "fuel_h", "curt", "soc", "reserve",
            "dC", "dE", "dEmin", "dP", "sC", "sE", "sP", "pump", "tank", "w_need", "w_srv", "mode", "blackout"]
    cols = {k: [] for k in keys}

    for t in range(n):
        capE = cap * capf_[t]
        if E > capE:
            E = capE
        Emin = SOC_MIN * cap
        invcap = sys.inv_kw * invf_[t]
        bd_lim = min(invcap, C_RATE * cap * dis_[t]) if has_bat else 0.0
        bc_lim = min(invcap, C_RATE * cap * chg_[t]) if has_bat else 0.0
        re = pv_[t] + wind_[t]
        dC, dEf, dEm, dP = crit_[t], essf_[t], essm_[t], prod_[t]
        if fuel_resupply and fuel < 0.3 * fuel_cap and not ev[t]:
            fuel = fuel_cap
        g = bd = ch = pump_e = R = 0.0
        blackout = False

        if strat.smart:
            in_ev, in_al = bool(ev[t]), bool(alert[t])
            if in_ev:
                mode = "evento"
            elif in_al:
                mode = "alerta"
            else:
                mode = "recuperação" if phase[t] == "recuperação" else "normal"
            # 1) reserva dinâmica para as cargas críticas
            if in_ev or in_al:
                end = ev_end[t] if ev_end[t] >= t else t
                H = int(min(max(end - t + 24, 24), 72))   # até ao fim do evento + 1 dia de margem
            else:
                H = 24      # planeamento contínuo para o dia seguinte (previsão a 24 h)
            a, b = t + 1, min(n, t + 1 + H)
            Rc = need(net_c, a, b)                  # reserva p/ críticas
            Rce = need(net_m, a, b)                 # reserva p/ críticas + essenciais mínimas
            if has_bat:
                Rc, Rce = min(Rc, 0.6 * cap), min(Rce, 0.8 * cap)
            else:
                Rc = Rce = 0.0
            R = Rc
            fuel_kwh = max(fuel - 6 * 0.08415 * rated, 0) / 0.30 if rated > 0 else 0.0
            # modo essencial só se bateria + gasóleo não garantirem críticas + essenciais mínimas
            essential_mode = (E - Emin) + fuel_kwh < Rce + 0.10 * cap
            dF = 0.0 if essential_mode else max(dEf - dEm, 0.0)    # parte de “conforto” das casas
            # há folga energética para TODA a procura até ao fim do horizonte? então não é preciso cortar nada
            # (só bateria + sol: o gasóleo nunca é gasto em cargas produtivas durante um evento)
            plenty = (E - Emin) >= need(net_a, a, b) + 0.10 * cap
            fC, fM, fF = Emin, Emin + Rc, Emin + Rce + 0.05 * cap   # pisos da bateria por nível
            # 2) renováveis → crítica → essencial mínima → conforto
            r = re
            sC = min(dC, r); r -= sC
            sM = min(dEm, r); r -= sM
            sF = min(dF, r); r -= sF
            nC, nM, nF = dC - sC, dEm - sM, dF - sF

            def avail(floor, used):
                return max(min(max(E - floor, 0) * ETA_D, bd_lim) - used, 0.0)

            # 3) gerador: quando a bateria não cobre as necessidades acima dos seus pisos, ou para pré-carregar
            hrs_to_ev = nxt[t] - t
            # pré-carga com gerador só se a previsão mostrar que bateria + sol não chegam para o evento
            need_ev = (Sm[min(n, ev_end[t] + 1)] - Sm[t]) / ETA_D if ev_end[t] >= t else 0.0
            precharge = (in_al and not in_ev and hrs_to_ev <= 24 and E < 0.95 * capE
                         and fuel_used_pre < 0.4 * fuel_cap and (E - Emin) * ETA_D < need_ev)
            tC = min(nC, avail(fC, 0)); tM = min(nM, avail(fM, tC)); tF = min(nF, avail(fF, tC + tM))
            short = (nC - tC) + (nM - tM) + (nF - tF) > 1e-6
            low = in_ev and E < fM
            if rated > 0 and (short or precharge or low):
                end_i = min(n, ev_end[t] + 1) if (in_ev and ev_end[t] >= t) else t
                resC = (Sc[end_i] - Sc[t]) * 0.35 + 0.08415 * rated * 6       # gasóleo a guardar p/ críticas
                resM = (Sm[end_i] - Sc[end_i] - Sm[t] + Sc[t]) * 0.35
                allowM, allowF = fuel > resC, fuel > resC + resM
                room = max(capE - E, 0) / ETA_C
                want_ch = min(bc_lim, room) if (precharge or low) else 0.0
                g = _gen_power(nC + (nM if allowM else 0) + (nF if allowF else 0) + want_ch, rated, fuel)
                if g > 0:
                    f = diesel_fuel(g, rated); fuel -= f; fuel_burn += f
                    if precharge:
                        fuel_used_pre += f
                    x = min(nC, g); sC += x; nC -= x; rest = g - x
                    if allowM:
                        x = min(nM, rest); sM += x; nM -= x; rest -= x
                    if allowF:
                        x = min(nF, rest); sF += x; nF -= x; rest -= x
                    x = min(rest, bc_lim, room); ch += x; rest -= x
                    x = min(rest, pump_kw, max(tank_cap - tank, 0) * kwh_m3); pump_e += x; rest -= x
            # 4) bateria cobre o resto, cada nível só até ao seu piso
            x = min(nC, avail(fC, bd)); sC += x; bd += x
            x = min(nM, avail(fM, bd)); sM += x; bd += x
            x = min(nF, avail(fF, bd)); sF += x; bd += x
            sE = sM + sF
            Emin_floor_P = max(0.35 * cap, fF)
            # 5) bomba de água: excedente renovável; emergência (depósito <15 %) usa bateria
            pd_ = max(min(pump_kw, max(tank_cap - tank, 0) * kwh_m3) - pump_e, 0)
            x = min(pd_, r); pump_e += x; r -= x; pd_ -= x
            if tank < 0.15 * tank_cap and pd_ > 0:
                x = min(pd_, max(E - Emin, 0) * ETA_D - bd, bd_lim - bd)
                if x > 0:
                    pump_e += x; bd += x
            # 6) carga da bateria e cargas produtivas
            room = max(capE - E, 0) / ETA_C
            if (in_ev or in_al) and not plenty:
                healthy = E >= fF + 0.25 * cap        # bateria folgada → a moagem pode usar o sol
                sP = min(dP, r) if healthy else 0.0; r -= sP
                x = max(min(r, bc_lim - ch, room - ch), 0); ch += x; r -= x
                if not healthy and (E + ch * ETA_C) >= 0.95 * capE:
                    sP = min(dP, r); r -= sP
            else:
                sP = min(dP, r); r -= sP
                if sP < dP:
                    x = min(dP - sP, max(E - Emin_floor_P, 0) * ETA_D - bd, bd_lim - bd)
                    if x > 0:
                        sP += x; bd += x
                x = max(min(r, bc_lim - ch, room - ch), 0); ch += x; r -= x
            if bd > 0 and ch > 0:      # nunca carregar e descarregar na mesma hora
                k = min(bd, ch); bd -= k; ch -= k
            curt = max(r, 0.0)
        else:
            mode = "evento" if ev[t] else ("recuperação" if phase[t] == "recuperação" else "normal")
            dE = dEf
            pump_req = min(pump_kw, max(tank_cap - tank, 0) * kwh_m3) if 8 <= hours[t] <= 15 else 0.0
            D = dC + dEf + dP + pump_req
            if lockout and E >= 0.30 * cap:
                lockout = False
            deficit = D - re
            served = deficit <= 1e-9
            if not served:
                availB = 0.0 if lockout else min(max(E - Emin, 0) * ETA_D, bd_lim)
                gen_on = rated > 0 and (deficit > availB + 1e-6 or E <= 0.25 * cap)
                if gen_on:
                    g = _gen_power(deficit, rated, fuel)
                x = min(g, deficit); deficit -= x
                bd = min(deficit, availB); deficit -= bd
                served = deficit <= 1e-6
                if not served:              # sobrecarga: o inversor/gerador dispara → apagão total
                    bd = 0.0; g = 0.0
            if g > 0:
                f = diesel_fuel(g, rated); fuel -= f; fuel_burn += f
            if served:
                sC, sE, sP, pump_e = dC, dEf, dP, pump_req
                surplus = re + bd + g - D
            else:
                sC = sE = sP = pump_e = 0.0
                surplus = re
                blackout = True
                lockout = True
            room = max(capE - E, 0) / ETA_C
            ch = max(min(surplus, bc_lim, room), 0.0) if bd == 0 else 0.0
            curt = max(surplus - ch, 0.0)
            if bd > 0 and (E - bd / ETA_D) <= Emin + 1e-6:
                lockout = True

        f_h = fuel_burn; fuel_burn = 0.0
        E = min(max(E + ch * ETA_C - bd / ETA_D, 0.0), capE)
        if kwh_m3 > 0:
            tank = min(tank + pump_e / kwh_m3, tank_cap)
        w_srv = min(water_[t], tank); tank -= w_srv

        c = cols
        c["pv_av"].append(pv_[t]); c["pv"].append(max(pv_[t] - curt, 0.0))
        c["wind"].append(wind_[t]); c["bat_dis"].append(bd); c["bat_ch"].append(ch); c["diesel"].append(g)
        c["fuel"].append(fuel); c["fuel_h"].append(f_h); c["curt"].append(curt)
        c["soc"].append(E / cap if has_bat else 0.0)
        c["reserve"].append((Emin + R) / cap if has_bat else 0.0)
        c["dC"].append(dC); c["dE"].append(dEf); c["dEmin"].append(dEm); c["dP"].append(dP)
        c["sC"].append(sC); c["sE"].append(sE); c["sP"].append(sP); c["pump"].append(pump_e)
        c["tank"].append(tank / tank_cap if tank_cap else 0); c["w_need"].append(water_[t])
        c["w_srv"].append(w_srv); c["mode"].append(mode); c["blackout"].append(blackout)

    cols.update(fase=phase, snow=snow, soil=soil, damage=res.damage,
                turb_stop=(res.turb_stop | turb_dead) & (sys.wind_kw > 0),
                t_bat=res.t_bat, chg_f=res.chg_f, inv_f=res.inv_f, aux=res.aux, poa=res.poa, t_cell=res.tcell,
                v_hub=res.v_hub, gust_hub=res.gust_hub, alert=alert)
    for k in dem.parts.columns:
        cols["d_" + k] = dem.parts[k].values
    out = pd.DataFrame(cols, index=w.index)
    out.attrs.update(households=comm.households, people=comm.people, pump_kw=pump_kw,
                     strategy=strat.name, kwh_m3=kwh_m3, fuel0=fuel0, bat_kwh=sys.bat_kwh)
    return out


# ───────────────────────────── indicadores ─────────────────────────────
def metrics(o: pd.DataFrame, mask=None) -> dict:
    m = o if mask is None else o[np.asarray(mask)]
    if len(m) == 0:
        m = o
    eps = 1e-9
    dC, dE, dP = m["dC"].sum(), m["dE"].sum(), m["dP"].sum()
    sC, sE, sP = m["sC"].sum(), m["sE"].sum(), m["sP"].sum()
    fracC = (m["sC"] / (m["dC"] + eps)).values
    out_h = fracC < 0.98
    longest = cur = 0
    for x in out_h:
        cur = cur + 1 if x else 0
        longest = max(longest, cur)
    dark = (m["sE"] < 0.95 * m["dEmin"]).values
    hh = o.attrs.get("households", 0)
    people = o.attrs.get("people", 1)
    days = max(len(m) / 24.0, 1 / 24)
    w_need, w_srv = m["w_need"].sum(), m["w_srv"].sum()
    crit_pct = 100 * sC / max(dC, eps)
    ess_pct = 100 * sE / max(dE, eps)
    prod_pct = 100 * sP / max(dP, eps)
    essmin_pct = 100 * np.minimum(m["sE"], m["dEmin"]).sum() / max(m["dEmin"].sum(), eps)
    water_pct = 100 * w_srv / max(w_need, eps)
    total_pct = 100 * (sC + sE + sP) / max(dC + dE + dP, eps)
    diesel_L = float(m["fuel_h"].sum())
    return dict(
        crit_pct=crit_pct, ess_pct=ess_pct, prod_pct=prod_pct, essmin_pct=essmin_pct,
        total_pct=total_pct,
        dem_kwh=dC + dE + dP,
        ens_kwh=(dC - sC) + (dE - sE) + (dP - sP), ens_crit=dC - sC, ens_ess=dE - sE, ens_prod=dP - sP,
        crit_out_h=int(out_h.sum()), crit_longest_h=int(longest),
        clinic_uptime=100 * (1 - out_h.mean()),
        house_dark_h=int(dark.sum() * hh), dark_hours=int(dark.sum()),
        blackout_h=int(m["blackout"].sum()),
        water_pct=water_pct,
        people_water=int(min(people, w_srv * 1000 / 15 / days)),
        diesel_kwh=float(m["diesel"].sum()), diesel_L=diesel_L, co2_kg=diesel_L * CO2_KG_PER_L,
        fuel_left=float(m["fuel"].iloc[-1]),
        soc_min=100 * float(m["soc"].min()), soc_end=100 * float(m["soc"].iloc[-1]),
        curt_kwh=float(m["curt"].sum()), pv_kwh=float(m["pv_av"].sum()), wind_kwh=float(m["wind"].sum()),
        # Índice RESILIA: serviços que mantêm pessoas seguras pesam mais do que o conforto
        index=0.50 * crit_pct + 0.25 * essmin_pct + 0.15 * water_pct + 0.10 * total_pct,
        cold_chain_ok=longest <= 6,
    )


def recovery_hours(o: pd.DataFrame):
    """Horas após o fim do evento até a comunidade voltar a ter serviço completo e bateria ≥50 %."""
    post = o[o["fase"] == "recuperação"]
    ok = ((post["sC"] >= 0.98 * post["dC"]) & (post["sE"] >= 0.98 * post["dE"])
          & ((post["soc"] >= 0.5) | (o.attrs.get("bat_kwh", 0) == 0))).values
    idx = np.flatnonzero(ok)
    return int(idx[0]) if len(idx) else None
