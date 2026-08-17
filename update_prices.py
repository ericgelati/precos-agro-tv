#!/usr/bin/env python3
"""
Busca cotação do dólar (USD/BRL) e futuros de soja e milho (CBOT) e grava
tudo em data.json, que é servido estaticamente pelo GitHub Pages.

Fontes:
  - USD/BRL: AwesomeAPI (economia.awesomeapi.com.br) - gratuita, sem chave.
  - Soja (ZS.F) e Milho (ZC.F) futuros CBOT: Stooq (stooq.com) - gratuita, sem chave.

O script é tolerante a falhas: se uma fonte falhar, mantém o último valor
conhecido (lido do data.json anterior) e marca o campo como "stale".
"""
import csv
import io
import json
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

DATA_FILE = "data.json"
TIMEOUT = 15
BR_TZ = timezone(timedelta(hours=-3))

# Fatores de conversão bushel -> saca de 60kg
SOYBEAN_BUSHEL_TO_SACA = 60 / 27.2155  # ~2.2046
CORN_BUSHEL_TO_SACA = 60 / 25.4012     # ~2.3621

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; precos-agro-tv/1.0)"}


def http_get(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read().decode("utf-8", errors="replace")


def load_previous():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def fetch_usdbrl():
    url = "https://economia.awesomeapi.com.br/json/last/USD-BRL"
    body = http_get(url)
    data = json.loads(body)["USDBRL"]
    return {
        "bid": float(data["bid"]),
        "pct_change": float(data["pctChange"]),
    }


def fetch_stooq(symbol):
    # f=sd2t2ohlcv -> Symbol,Date,Time,Open,High,Low,Close,Volume
    url = f"https://stooq.com/q/l/?s={symbol}&f=sd2t2ohlcv&h&e=csv"
    body = http_get(url)
    reader = csv.DictReader(io.StringIO(body))
    row = next(reader)
    close = row.get("Close")
    open_ = row.get("Open")
    if close in (None, "", "N/D"):
        raise ValueError(f"stooq sem dado válido para {symbol}: {row}")
    close = float(close)
    open_ = float(open_) if open_ not in (None, "", "N/D") else close
    pct_change = ((close - open_) / open_ * 100) if open_ else 0.0
    return {"price_usd_bushel": close, "pct_change": pct_change}


def build_field(previous_field, fresh_value, extra=None, now_iso=None, now_br=None):
    """Combina o valor novo (se veio ok) com o anterior (se a fonte falhou)."""
    field = dict(previous_field or {})
    if fresh_value is not None:
        field.update(fresh_value)
        if extra:
            field.update(extra)
        field["stale"] = False
        field["updated_at_utc"] = now_iso
        field["updated_at_br"] = now_br
    else:
        field["stale"] = True
    return field


def main():
    previous = load_previous()
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    now_br = now.astimezone(BR_TZ).strftime("%d/%m/%Y %H:%M:%S")

    errors = []

    # --- USD/BRL ---
    try:
        usd = fetch_usdbrl()
    except Exception as e:
        usd = None
        errors.append(f"USD/BRL: {e}")

    usdbrl_rate = usd["bid"] if usd else (previous.get("usdbrl") or {}).get("bid")

    usdbrl_field = build_field(
        previous.get("usdbrl"), usd, now_iso=now_iso, now_br=now_br
    )

    # --- Soja (ZS.F) ---
    try:
        soy = fetch_stooq("zs.f")
        soy_extra = {
            "symbol": "ZS.F (CBOT)",
            "price_brl_saca_est": round(
                soy["price_usd_bushel"] * SOYBEAN_BUSHEL_TO_SACA * usdbrl_rate / 100, 2
            )
            if usdbrl_rate
            else None,
        }
        # Nota: cotação CBOT de soja é em cents/bushel -> dividir por 100 para US$.
        soy["price_usd_bushel"] = round(soy["price_usd_bushel"] / 100, 4)
    except Exception as e:
        soy = None
        soy_extra = None
        errors.append(f"Soja: {e}")

    soybean_field = build_field(
        previous.get("soybean"), soy, extra=soy_extra, now_iso=now_iso, now_br=now_br
    )

    # --- Milho (ZC.F) ---
    try:
        corn = fetch_stooq("zc.f")
        corn_extra = {
            "symbol": "ZC.F (CBOT)",
            "price_brl_saca_est": round(
                corn["price_usd_bushel"] * CORN_BUSHEL_TO_SACA * usdbrl_rate / 100, 2
            )
            if usdbrl_rate
            else None,
        }
        corn["price_usd_bushel"] = round(corn["price_usd_bushel"] / 100, 4)
    except Exception as e:
        corn = None
        corn_extra = None
        errors.append(f"Milho: {e}")

    corn_field = build_field(
        previous.get("corn"), corn, extra=corn_extra, now_iso=now_iso, now_br=now_br
    )

    out = {
        "generated_at_utc": now_iso,
        "generated_at_br": now_br,
        "usdbrl": usdbrl_field,
        "soybean": soybean_field,
        "corn": corn_field,
        "errors": errors,
    }

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")

    if errors:
        print("Concluído com avisos:\n" + "\n".join(errors), file=sys.stderr)
    else:
        print("data.json atualizado com sucesso.")


if __name__ == "__main__":
    main()
