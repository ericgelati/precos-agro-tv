#!/usr/bin/env python3
"""
Busca cotação do dólar (USD/BRL) e futuros de soja e milho (CBOT) e grava
tudo em data.json, que é servido estaticamente pelo GitHub Pages.

Fonte: Yahoo Finance (query1.finance.yahoo.com/v8/finance/chart/<símbolo>) —
gratuita, sem chave, mesma fonte que alimenta finance.yahoo.com.
  - Dólar: símbolo BRL=X (USD/BRL)
  - Soja:  símbolo ZS=F  (futuro CBOT, cents/bushel)
  - Milho: símbolo ZC=F  (futuro CBOT, cents/bushel)

O script é tolerante a falhas: se uma fonte falhar (rede instável, limite de
requisições etc.), mantém o último valor conhecido (lido do data.json
anterior) e marca o campo como "stale", em vez de quebrar o painel.
"""
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta

DATA_FILE = "data.json"
TIMEOUT = 15
RETRIES = 3
RETRY_DELAY_SEC = 4
BR_TZ = timezone(timedelta(hours=-3))

# Fatores de conversão bushel -> saca de 60kg
SOYBEAN_BUSHEL_TO_SACA = 60 / 27.2155  # ~2.2046
CORN_BUSHEL_TO_SACA = 60 / 25.4012     # ~2.3621

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
}


def fetch_yahoo(symbol):
    """Busca preço atual + fechamento anterior de um símbolo no Yahoo Finance."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    last_err = None
    for attempt in range(1, RETRIES + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                body = resp.read().decode("utf-8", errors="replace")
            meta = json.loads(body)["chart"]["result"][0]["meta"]
            price = float(meta["regularMarketPrice"])
            prev_close = float(meta.get("previousClose") or meta.get("chartPreviousClose") or price)
            pct_change = ((price - prev_close) / prev_close * 100) if prev_close else 0.0
            return {"price": price, "pct_change": pct_change}
        except Exception as e:  # noqa: BLE001 - queremos capturar qualquer falha de rede/parse
            last_err = e
            if attempt < RETRIES:
                time.sleep(RETRY_DELAY_SEC)
    raise RuntimeError(f"falha ao buscar {symbol} após {RETRIES} tentativas: {last_err}")


def load_previous():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


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
        y = fetch_yahoo("BRL=X")
        usd = {"bid": round(y["price"], 4), "pct_change": round(y["pct_change"], 2)}
    except Exception as e:
        usd = None
        errors.append(f"USD/BRL: {e}")

    usdbrl_rate = usd["bid"] if usd else (previous.get("usdbrl") or {}).get("bid")

    usdbrl_field = build_field(
        previous.get("usdbrl"), usd, now_iso=now_iso, now_br=now_br
    )

    # --- Soja (ZS=F, cents/bushel) ---
    try:
        y = fetch_yahoo("ZS=F")
        price_usd_bushel = round(y["price"] / 100, 4)
        soy = {"price_usd_bushel": price_usd_bushel, "pct_change": round(y["pct_change"], 2)}
        soy_extra = {
            "symbol": "ZS=F (CBOT)",
            "price_brl_saca_est": round(price_usd_bushel * SOYBEAN_BUSHEL_TO_SACA * usdbrl_rate, 2)
            if usdbrl_rate
            else None,
        }
    except Exception as e:
        soy = None
        soy_extra = None
        errors.append(f"Soja: {e}")

    soybean_field = build_field(
        previous.get("soybean"), soy, extra=soy_extra, now_iso=now_iso, now_br=now_br
    )

    # --- Milho (ZC=F, cents/bushel) ---
    try:
        y = fetch_yahoo("ZC=F")
        price_usd_bushel = round(y["price"] / 100, 4)
        corn = {"price_usd_bushel": price_usd_bushel, "pct_change": round(y["pct_change"], 2)}
        corn_extra = {
            "symbol": "ZC=F (CBOT)",
            "price_brl_saca_est": round(price_usd_bushel * CORN_BUSHEL_TO_SACA * usdbrl_rate, 2)
            if usdbrl_rate
            else None,
        }
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
