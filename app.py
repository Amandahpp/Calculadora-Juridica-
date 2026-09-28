from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)


def D(v):
    try:
        return Decimal(str(v).replace(",", ".")) if v not in (None, "") else Decimal(0)
    except InvalidOperation:
        return Decimal(0)


def q(d):
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def brl(d):
    s = f"{q(d):,.2f}"
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def br_date(s):
    return "/".join(reversed(s.split("-"))) if s else ""


def calcular(d):
    saldo, n = D(d.get("saldo")), D(d.get("n"))
    exec_, cap, cab = D(d.get("executado")), D(d.get("capital")), D(d.get("cabecalho"))
    saldo_antes = D(d.get("saldo_antes"))
    ams = [D(x) for x in d.get("amortizacoes", [])]
    segs = [D(x) for x in d.get("seguros", [])]
    aju, base = d.get("data_ajuizamento", ""), d.get("data_base", "")

    if saldo <= 0 or n <= 0:
        return {"erro": "Informe saldo devedor e número de prestações maiores que zero."}

    parcela = saldo / n
    fator = exec_ / saldo
    atualizada = q(parcela * fator)
    excesso = q(exec_) - atualizada
    total_am, total_seg = sum(ams, Decimal(0)), sum(segs, Decimal(0))

    alertas = []
    if cap > 0 and abs(cab - 2 * cap) < Decimal("0.005"):
        alertas.append({"tipo": "aviso", "texto": f"O 'valor da operação' ({brl(cab)}) é exatamente o dobro do capital utilizado ({brl(cap)}). Inconsistência a esclarecer."})
    elif cap > 0 and abs(cab - cap) > Decimal("0.005"):
        alertas.append({"tipo": "aviso", "texto": f"O cabeçalho difere do capital utilizado em {brl(abs(cab - cap))}."})
    elif cap > 0:
        alertas.append({"tipo": "ok", "texto": "Cabeçalho e capital utilizado coincidem."})
    if aju and base and base > aju:
        alertas.append({"tipo": "aviso", "texto": f"A data-base ({br_date(base)}) é posterior ao ajuizamento ({br_date(aju)}). Art. 798, I, 'b', do CPC."})
    alertas.append({"tipo": "info", "texto": "A parcela atualizada usa o mesmo fator do banco, logo equivale a executado ÷ nº de prestações. Encargos do aditivo sobre a parcela não entram nesta conta."})

    texto = (
        f"Saldo devedor de {brl(saldo)} dividido por {int(n)} prestações resulta em parcela de {brl(parcela)}. "
        f"O fator global de atualização do banco é de {fator:.6f} ({brl(exec_)} ÷ {brl(saldo)}). "
        f"Aplicado à parcela, o montante subsidiariamente exigível é de {brl(atualizada)}, "
        f"contra {brl(exec_)} executados, com excesso de execução de {brl(excesso)}."
    )
    return {
        "parcela": float(q(parcela)), "fator": float(round(fator, 6)),
        "atualizada": float(atualizada), "excesso": float(excesso),
        "excesso_pct": float(excesso / exec_ * 100) if exec_ > 0 else 0,
        "total_amortizacoes": float(q(total_am)),
        "saldo_pos_amortizacoes": float(q(saldo_antes - total_am)),
        "total_seguros": float(q(total_seg)),
        "cabecalho_sobre_capital": float(round(cab / cap, 4)) if cap > 0 else None,
        "alertas": alertas, "texto": texto,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/calcular", methods=["POST"])
def api_calcular():
    return jsonify(calcular(request.get_json(force=True) or {}))


if __name__ == "__main__":
    app.run(debug=True)
