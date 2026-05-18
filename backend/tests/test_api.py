"""
tests/test_api.py
Suite de tests para el proyecto RiskLab — Teoría del Riesgo · USTA
Cubre: unitarios (funciones puras) + integración (endpoints con TestClient)

Ejecutar:
    cd backend
    pytest tests/ -v --tb=short
"""
import math
import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

# ── Importar app ──────────────────────────────────────────────────────────────
from app.main import app
from app.services.fixed_income import YieldCurve, Bond
from app.services.options import OptionPricer
from app.services.stress import StressTester

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    """Cliente de prueba con BD en memoria (no toca SQLite de producción)."""
    import os
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def yield_curve():
    """YieldCurve ajustada con datos sintéticos de tesoros US."""
    yc = YieldCurve()
    maturities = [0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
    yields     = [5.30, 5.25, 5.10, 4.80, 4.40, 4.20, 4.00]
    yc.fit_nelson_siegel(maturities, yields)
    return yc


@pytest.fixture(scope="module")
def bond():
    """Bono sintético: cupón 5%, vencimiento 5 años, nominal 1000."""
    return Bond(face_value=1000.0, coupon_rate=0.05, maturity_years=5, frequency=2)


@pytest.fixture(scope="module")
def call_pricer():
    """Pricer Black-Scholes para una call ATM."""
    return OptionPricer(S=100.0, K=100.0, T=1.0, r=0.05, sigma=0.20, tipo="call")


@pytest.fixture(scope="module")
def put_pricer():
    """Pricer Black-Scholes para una put ATM."""
    return OptionPricer(S=100.0, K=100.0, T=1.0, r=0.05, sigma=0.20, tipo="put")


# ══════════════════════════════════════════════════════════════════════════════
# TESTS UNITARIOS — funciones puras, sin red ni BD
# ══════════════════════════════════════════════════════════════════════════════

class TestVaRParametrico:
    """Módulo 5 — VaR paramétrico."""

    def test_var_parametrico_95(self):
        """VaR param al 95% debe ser negativo y mayor que al 99%."""
        from scipy import stats
        ret = np.random.normal(0, 0.01, 1000)
        mu, sigma = ret.mean(), ret.std()
        var_95 = float(stats.norm.ppf(0.05, mu, sigma))
        var_99 = float(stats.norm.ppf(0.01, mu, sigma))
        assert var_95 < 0
        assert var_99 < var_95

    def test_cvar_menor_que_var(self):
        """CVaR siempre debe ser ≤ VaR."""
        ret = np.random.normal(0, 0.01, 5000)
        var = float(np.percentile(ret, 5))
        cvar = float(ret[ret <= var].mean())
        assert cvar <= var

    def test_kupiec_no_falla_con_pocas_violaciones(self):
        """Test de Kupiec con 0 violaciones no debe lanzar excepción."""
        from scipy import stats as sc
        n, violations, alpha = 250, 0, 0.05
        p_hat = (violations + 1e-9) / n
        p_expected = alpha
        try:
            lr = -2 * (
                math.log(p_expected**violations * (1 - p_expected)**(n - violations) + 1e-300) -
                math.log(p_hat**violations * (1 - p_hat)**(n - violations) + 1e-300)
            )
            pval = float(sc.chi2.sf(lr, df=1))
            assert 0.0 <= pval <= 1.0
        except Exception as e:
            pytest.fail(f"Kupiec falló inesperadamente: {e}")


class TestBlackScholes:
    """Módulo 10 — Black-Scholes y Greeks."""

    def test_call_precio_positivo(self, call_pricer):
        result = call_pricer.full_result()
        assert result["price"] > 0

    def test_put_precio_positivo(self, put_pricer):
        result = put_pricer.full_result()
        assert result["price"] > 0

    def test_paridad_put_call(self, call_pricer, put_pricer):
        """C - P = S - K·e^(-rT) con tolerancia numérica."""
        c = call_pricer.full_result()["price"]
        p = put_pricer.full_result()["price"]
        S, K, r, T = 100.0, 100.0, 0.05, 1.0
        parity_lhs = c - p
        parity_rhs = S - K * math.exp(-r * T)
        assert abs(parity_lhs - parity_rhs) < 0.01

    def test_delta_call_entre_0_y_1(self, call_pricer):
        # FIX: greeks están anidados bajo result["greeks"]
        result = call_pricer.full_result()
        assert 0.0 <= result["greeks"]["delta"] <= 1.0

    def test_delta_put_entre_menos1_y_0(self, put_pricer):
        result = put_pricer.full_result()
        assert -1.0 <= result["greeks"]["delta"] <= 0.0

    def test_gamma_positivo(self, call_pricer):
        result = call_pricer.full_result()
        assert result["greeks"]["gamma"] > 0

    def test_vega_positivo(self, call_pricer):
        result = call_pricer.full_result()
        assert result["greeks"]["vega"] > 0

    def test_call_deep_in_money(self):
        """Call profunda ITM debe valer aprox S - K·e^(-rT)."""
        pricer = OptionPricer(S=200.0, K=100.0, T=1.0, r=0.05, sigma=0.20, tipo="call")
        result = pricer.full_result()
        intrinsic = 200.0 - 100.0 * math.exp(-0.05 * 1.0)
        assert result["price"] >= intrinsic * 0.95

    def test_call_deep_out_of_money(self):
        """Call profunda OTM debe valer casi cero."""
        pricer = OptionPricer(S=50.0, K=200.0, T=0.1, r=0.05, sigma=0.10, tipo="call")
        result = pricer.full_result()
        assert result["price"] < 0.01

    def test_vol_implicita_round_trip(self, call_pricer):
        """La vol implícita calculada desde el precio BS debe recuperar σ original."""
        result = call_pricer.full_result()
        market_price = result["price"]
        # FIX: implied_volatility retorna un dict, no un float
        iv_result = call_pricer.implied_volatility(market_price)
        assert "sigma_implicita_pct" in iv_result
        sigma_imp = iv_result["sigma_implicita_pct"] / 100.0
        assert abs(sigma_imp - 0.20) < 0.001, (
            f"Vol implícita {sigma_imp:.4f} no recupera σ=0.20"
        )


class TestNelsonSiegel:
    """Módulo 9 — Curva de rendimiento."""

    def test_fit_retorna_4_parametros(self, yield_curve):
        # FIX: el atributo es params_, no nelson_siegel_params
        assert yield_curve.params_ is not None
        assert len(yield_curve.params_) == 4

    def test_spot_rate_en_rangos_razonables(self, yield_curve):
        """Tasa spot a 10 años debe estar entre 0% y 20%."""
        rate = yield_curve.spot_rate(10.0)
        assert 0.0 < rate < 20.0

    def test_curva_interpolada_tiene_puntos(self, yield_curve):
        # FIX: curve_points retorna tau_ns/yield_ns no maturities/yields
        pts = yield_curve.curve_points(n=50)
        assert len(pts["tau_ns"]) == 50
        assert len(pts["yield_ns"]) == 50

    def test_beta0_nivel_largo_plazo_positivo(self, yield_curve):
        """β₀ representa nivel de largo plazo — debe ser positivo."""
        beta0 = yield_curve.params_[0]
        assert beta0 > 0


class TestBond:
    """Módulo 9 — Duración y convexidad."""

    def test_duracion_macaulay_positiva(self, bond):
        metrics = bond.full_metrics(ytm=0.05)
        assert metrics["macaulay_duration"] > 0

    def test_duracion_modificada_menor_que_macaulay(self, bond):
        metrics = bond.full_metrics(ytm=0.05)
        assert metrics["modified_duration"] < metrics["macaulay_duration"]

    def test_convexidad_positiva(self, bond):
        metrics = bond.full_metrics(ytm=0.05)
        assert metrics["convexity"] > 0

    def test_precio_a_la_par_cuando_cupon_igual_ytm(self):
        """Un bono con cupón = YTM debe valer aprox su valor nominal."""
        b = Bond(face_value=1000.0, coupon_rate=0.05, maturity_years=5, frequency=2)
        metrics = b.full_metrics(ytm=0.05)
        assert abs(metrics["price"] - 1000.0) < 1.0

    def test_precio_sube_cuando_ytm_baja(self):
        """Relación inversa precio-tasa."""
        b = Bond(face_value=1000.0, coupon_rate=0.05, maturity_years=10, frequency=2)
        price_high_ytm = b.full_metrics(ytm=0.07)["price"]
        price_low_ytm  = b.full_metrics(ytm=0.03)["price"]
        assert price_low_ytm > price_high_ytm

    def test_sensibilidad_shocks_retorna_dict(self, bond):
        metrics = bond.full_metrics(ytm=0.05)
        assert "price_sensitivity" in metrics
        assert len(metrics["price_sensitivity"]) > 0


class TestSMA:
    """Módulo 1 — Indicadores técnicos (función pura)."""

    def test_sma_longitud_correcta(self):
        close = pd.Series(range(1, 101), dtype=float)
        sma = close.rolling(20).mean()
        assert len(sma) == 100
        assert sma.iloc[:19].isna().all()
        assert not math.isnan(sma.iloc[19])

    def test_ema_primer_valor_valido(self):
        close = pd.Series(range(1, 51), dtype=float)
        ema = close.ewm(span=20, adjust=False).mean()
        assert not math.isnan(ema.iloc[0])

    def test_rsi_acotado_0_100(self):
        np.random.seed(42)
        close = pd.Series(np.cumsum(np.random.randn(200)) + 100)
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rsi = 100 - (100 / (1 + gain / loss))
        rsi_valid = rsi.dropna()
        assert (rsi_valid >= 0).all() and (rsi_valid <= 100).all()


# ══════════════════════════════════════════════════════════════════════════════
# TESTS DE INTEGRACIÓN — endpoints FastAPI con TestClient
# ══════════════════════════════════════════════════════════════════════════════

class TestHealthEndpoint:

    def test_root_ok(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestOpcionEndpoint:

    def test_opcion_call_200(self, client):
        payload = {
            "S": 100.0, "K": 100.0, "T": 1.0,
            "r": 0.05, "sigma": 0.20, "tipo": "call"
        }
        r = client.post("/opcion/precio", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert "price" in data
        # FIX: greeks están anidados
        assert "greeks" in data
        assert "delta" in data["greeks"]
        assert "gamma" in data["greeks"]
        assert "vega"  in data["greeks"]
        assert "theta" in data["greeks"]
        assert "rho"   in data["greeks"]

    def test_opcion_put_200(self, client):
        payload = {
            "S": 150.0, "K": 140.0, "T": 0.5,
            "r": 0.04, "sigma": 0.25, "tipo": "put"
        }
        r = client.post("/opcion/precio", json=payload)
        assert r.status_code == 200
        assert r.json()["price"] > 0

    def test_opcion_con_precio_mercado_retorna_vol_implicita(self, client):
        payload = {
            "S": 100.0, "K": 100.0, "T": 1.0,
            "r": 0.05, "sigma": 0.20, "tipo": "call",
            "market_price": 10.45
        }
        r = client.post("/opcion/precio", json=payload)
        assert r.status_code == 200
        assert "implied_vol" in r.json()

    def test_opcion_tipo_invalido_422(self, client):
        payload = {
            "S": 100.0, "K": 100.0, "T": 1.0,
            "r": 0.05, "sigma": 0.20, "tipo": "future"
        }
        r = client.post("/opcion/precio", json=payload)
        assert r.status_code == 422


class TestBonoEndpoint:

    def test_bono_duracion_200(self, client):
        payload = {
            "face_value": 1000.0,
            "coupon_rate": 0.05,
            "maturity_years": 5,
            "frequency": 2,
            "ytm": 0.05
        }
        r = client.post("/bono/duracion", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert "macaulay_duration" in data
        assert "modified_duration" in data
        assert "convexity" in data
        assert "price" in data

    def test_bono_ytm_borde(self, client):
        """YTM casi cero es borde matemático: debe responder sin crashear."""
        payload = {
            "face_value": 1000.0,
            "coupon_rate": 0.05,
            "maturity_years": 5,
            "frequency": 2,
            "ytm": 0.0001
        }
        r = client.post("/bono/duracion", json=payload)
        assert r.status_code in (200, 422)


class TestVaREndpoint:

    def test_var_ticker_valido(self, client):
        payload = {"ticker": "MSFT", "confidence": 0.95, "simulations": 1000}
        r = client.post("/var", json=payload)
        assert r.status_code == 200
        data = r.json()
        # FIX: las claves reales son var_parametric, var_historical, var_montecarlo
        assert "var_parametric" in data
        assert "var_historical" in data
        assert "var_montecarlo" in data
        assert "cvar" in data
        assert "kupiec_pval" in data

    def test_var_ticker_invalido_404(self, client):
        payload = {"ticker": "XYZINVALIDO", "confidence": 0.95, "simulations": 1000}
        r = client.post("/var", json=payload)
        assert r.status_code == 404


class TestStressEndpoint:

    def test_stress_escenarios_default(self, client):
        payload = {
            "tickers": ["MSFT", "KO"],
            "weights": [0.6, 0.4],
            "scenarios": []
        }
        r = client.post("/stress", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, (list, dict))

    def test_stress_ticker_invalido_400(self, client):
        payload = {
            "tickers": ["FAKE123", "MSFT"],
            "weights": [0.5, 0.5],
            "scenarios": []
        }
        r = client.post("/stress", json=payload)
        assert r.status_code == 400


class TestPortafoliosEndpoint:

    def test_crear_portafolio(self, client):
        payload = {
            "name": "Portafolio Test",
            "tickers": ["MSFT", "KO", "JPM"],
            "weights": {"MSFT": 0.5, "KO": 0.3, "JPM": 0.2},
            "notes": "Portafolio de prueba automatizada"
        }
        r = client.post("/portafolios", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert "id" in data
        assert data["name"] == "Portafolio Test"

    def test_listar_portafolios(self, client):
        r = client.get("/portafolios")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_eliminar_portafolio_inexistente_404(self, client):
        r = client.delete("/portafolios/99999")
        assert r.status_code == 404


class TestPredictEndpoint:

    def test_predict_ticker_valido(self, client):
        payload = {"ticker": "NVDA"}
        r = client.post("/predict", json=payload)
        # 200 si modelo entrenado, 503 si model.joblib no existe aún
        assert r.status_code in (200, 422, 503)

    def test_predict_history_retorna_lista(self, client):
        r = client.get("/predict/history?limit=5")
        assert r.status_code == 200
        assert isinstance(r.json(), list)