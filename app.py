import os
import json
import uuid
from datetime import datetime, timedelta

from flask import Flask, jsonify, request, render_template_string
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

# Keep your existing PostgreSQL password in an environment variable, or replace
# YOUR_POSTGRES_PASSWORD locally. Do not commit a real password to GitHub.
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "database": os.getenv("POSTGRES_DB", "pay-shield"),
    "user": os.getenv("POSTGRES_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD"),
    "port": os.getenv("POSTGRES_PORT", "5432"),
}


def db():
    return psycopg2.connect(**DB_CONFIG)


def current_time():
    return datetime.utcnow()


def client_ip():
    forwarded = request.headers.get("X-Forwarded-For")
    return forwarded.split(",")[0].strip() if forwarded else (request.remote_addr or "127.0.0.1")


def num(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def clamp(value, low=0, high=100):
    return max(low, min(high, float(value)))


def initialize_database():
    conn = db()
    cur = conn.cursor()
    try:
        # Existing tables are preserved; missing columns are added safely.
        cur.execute("""
            CREATE TABLE IF NOT EXISTS bank_accounts (
                account_id TEXT PRIMARY KEY,
                customer TEXT NOT NULL,
                balance NUMERIC(14,2) NOT NULL DEFAULT 0
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                payment_id TEXT PRIMARY KEY,
                amount NUMERIC(14,2) NOT NULL,
                customer TEXT NOT NULL,
                status TEXT NOT NULL,
                transaction_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        for statement in [
            "ALTER TABLE payments ADD COLUMN IF NOT EXISTS device_id TEXT",
            "ALTER TABLE payments ADD COLUMN IF NOT EXISTS ip_address TEXT",
            "ALTER TABLE payments ADD COLUMN IF NOT EXISTS order_id TEXT",
            "ALTER TABLE payments ADD COLUMN IF NOT EXISTS client_status TEXT",
            "ALTER TABLE payments ADD COLUMN IF NOT EXISTS bank_status TEXT",
            "ALTER TABLE payments ADD COLUMN IF NOT EXISTS integrity_status TEXT",
            "ALTER TABLE payments ADD COLUMN IF NOT EXISTS failure_reason TEXT",
        ]:
            cur.execute(statement)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS risk_transactions (
                risk_id BIGSERIAL PRIMARY KEY,
                payment_id TEXT,
                customer TEXT NOT NULL,
                amount NUMERIC(14,2) NOT NULL,
                device_id TEXT,
                ip_address TEXT,
                risk_score NUMERIC(6,2) NOT NULL,
                risk_level TEXT NOT NULL,
                decision TEXT NOT NULL,
                expected_loss NUMERIC(14,2) NOT NULL,
                components JSONB NOT NULL DEFAULT '{}'::jsonb,
                explanation TEXT,
                agent_action TEXT,
                transaction_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS risk_events (
                event_id BIGSERIAL PRIMARY KEY,
                payment_id TEXT,
                customer TEXT NOT NULL,
                risk_score NUMERIC(6,2) NOT NULL,
                expected_loss NUMERIC(14,2) NOT NULL,
                outcome TEXT,
                actual_loss NUMERIC(14,2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS payment_outcomes (
                outcome_id BIGSERIAL PRIMARY KEY,
                payment_id TEXT NOT NULL,
                customer TEXT NOT NULL,
                outcome_type TEXT NOT NULL,
                amount NUMERIC(14,2) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS risk_feedback (
                feedback_id BIGSERIAL PRIMARY KEY,
                payment_id TEXT,
                customer TEXT,
                predicted_decision TEXT,
                actual_outcome TEXT,
                predicted_risk NUMERIC(6,2),
                actual_loss NUMERIC(14,2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS merchant_loss_events (
                loss_id BIGSERIAL PRIMARY KEY,
                payment_id TEXT,
                customer TEXT,
                loss_type TEXT,
                amount NUMERIC(14,2) DEFAULT 0,
                estimated_cost NUMERIC(14,2) DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_payments_customer_time ON payments(customer, transaction_time)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_payments_device ON payments(device_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_payments_ip ON payments(ip_address)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_risk_customer_time ON risk_transactions(customer, transaction_time)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_outcomes_customer ON payment_outcomes(customer)")
        conn.commit()
    finally:
        cur.close()
        conn.close()


def bank_payment(customer, amount):
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT account_id, balance FROM bank_accounts WHERE customer=%s FOR UPDATE", (customer,))
        row = cur.fetchone()
        if not row:
            conn.rollback()
            return False, "Bank account not found"
        balance = num(row[1])
        if balance < amount:
            conn.rollback()
            return False, "Insufficient balance"
        cur.execute("UPDATE bank_accounts SET balance=balance-%s WHERE account_id=%s", (amount, row[0]))
        conn.commit()
        return True, "Payment processed successfully"
    except Exception as exc:
        conn.rollback()
        return False, str(exc)
    finally:
        cur.close()
        conn.close()


def get_features(customer, amount, device_id=None, ip_address=None, order_id=None):
    conn = db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    now = current_time()
    try:
        cur.execute("""
            SELECT payment_id, amount, status, transaction_time, device_id, ip_address,
                   order_id, client_status, bank_status, integrity_status
            FROM payments
            WHERE customer=%s
            ORDER BY transaction_time DESC
            LIMIT 1000
        """, (customer,))
        history = cur.fetchall()

        cur.execute("""
            SELECT outcome_type, amount, created_at, payment_id
            FROM payment_outcomes
            WHERE customer=%s
            ORDER BY created_at DESC
            LIMIT 1000
        """, (customer,))
        outcomes = cur.fetchall()

        successful = [r for r in history if str(r["status"]).upper() in {"SUCCESS", "CAPTURED", "AUTHORIZED"}]
        failed = [r for r in history if str(r["status"]).upper() in {"FAILED", "FAIL", "DECLINED"}]

        def count_recent(minutes):
            cutoff = now - timedelta(minutes=minutes)
            return sum(1 for r in history if r["transaction_time"] and r["transaction_time"] >= cutoff)

        last_1m = count_recent(1)
        last_10m = count_recent(10)
        last_1h = count_recent(60)
        last_24h = count_recent(1440)

        amounts = [num(r["amount"]) for r in successful]
        average_amount = sum(amounts) / len(amounts) if amounts else 0
        amount_deviation = abs(amount - average_amount) / average_amount if average_amount else 0

        refunds = [o for o in outcomes if str(o["outcome_type"]).lower() == "refund"]
        chargebacks = [o for o in outcomes if str(o["outcome_type"]).lower() == "chargeback"]
        refund_amount = sum(num(o["amount"]) for o in refunds)
        chargeback_amount = sum(num(o["amount"]) for o in chargebacks)
        refund_rate = len(refunds) / len(successful) if successful else 0
        chargeback_rate = len(chargebacks) / len(successful) if successful else 0

        distinct_device_customers = 0
        if device_id:
            cur.execute("SELECT COUNT(DISTINCT customer) AS c FROM risk_transactions WHERE device_id=%s", (device_id,))
            distinct_device_customers = int(cur.fetchone()["c"] or 0)

        distinct_ip_customers = 0
        if ip_address:
            cur.execute("SELECT COUNT(DISTINCT customer) AS c FROM risk_transactions WHERE ip_address=%s", (ip_address,))
            distinct_ip_customers = int(cur.fetchone()["c"] or 0)

        # Same device/IP with the same customer is not treated as abuse by itself.
        # We specifically look for many distinct identities.
        cur.execute("""
            SELECT COUNT(*) AS c
            FROM risk_transactions
            WHERE device_id=%s AND transaction_time >= %s
        """, (device_id, now - timedelta(days=30))) if device_id else None
        device_activity = int(cur.fetchone()["c"] or 0) if device_id else 0

        cur.execute("""
            SELECT COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE status IN ('FAILED','FAIL','DECLINED')) AS failed
            FROM payments
            WHERE transaction_time >= %s
        """, (now - timedelta(minutes=10),))
        spike = cur.fetchone()
        spike_total = int(spike["total"] or 0)
        spike_failed = int(spike["failed"] or 0)
        spike_failure_rate = spike_failed / spike_total if spike_total else 0

        # Duplicate: same customer + amount + order within two minutes.
        duplicate_count = 0
        if order_id:
            cur.execute("""
                SELECT COUNT(*) AS c FROM payments
                WHERE customer=%s AND amount=%s AND order_id=%s
                  AND transaction_time >= %s
            """, (customer, amount, order_id, now - timedelta(minutes=2)))
            duplicate_count = int(cur.fetchone()["c"] or 0)
        else:
            cur.execute("""
                SELECT COUNT(*) AS c FROM payments
                WHERE customer=%s AND amount=%s
                  AND transaction_time >= %s
            """, (customer, amount, now - timedelta(minutes=2)))
            duplicate_count = int(cur.fetchone()["c"] or 0)

        integrity_mismatches = sum(
            1 for r in history
            if str(r.get("integrity_status") or "").upper() in {"MISMATCH", "UNCERTAIN"}
        )

        return {
            "total_transactions": len(history),
            "successful_transactions": len(successful),
            "failed_transactions": len(failed),
            "last_1m": last_1m,
            "last_10m": last_10m,
            "last_1h": last_1h,
            "last_24h": last_24h,
            "average_amount": round(average_amount, 2),
            "amount_deviation": round(amount_deviation, 4),
            "refund_count": len(refunds),
            "refund_rate": round(refund_rate, 4),
            "refund_amount": round(refund_amount, 2),
            "chargeback_count": len(chargebacks),
            "chargeback_rate": round(chargeback_rate, 4),
            "chargeback_amount": round(chargeback_amount, 2),
            "distinct_device_customers": distinct_device_customers,
            "distinct_ip_customers": distinct_ip_customers,
            "device_activity": device_activity,
            "fraud_spike_total": spike_total,
            "fraud_spike_failed": spike_failed,
            "fraud_spike_failure_rate": round(spike_failure_rate, 4),
            "duplicate_count": duplicate_count,
            "integrity_mismatches": integrity_mismatches,
        }
    finally:
        cur.close()
        conn.close()


def merchant_cost_estimate(amount, outcome_type=None):
    # Prototype economic model. Rates are configurable and deliberately conservative.
    processing_fee_rate = 0.02
    gst_on_processing_fee = 0.18
    fulfilment_cost_rate = 0.10
    return_logistics_rate = 0.05
    processing_fee = amount * processing_fee_rate
    processing_tax = processing_fee * gst_on_processing_fee
    fulfilment = amount * fulfilment_cost_rate
    return_cost = amount * return_logistics_rate if outcome_type in {"refund", "chargeback"} else 0
    return {
        "processing_fee": round(processing_fee, 2),
        "processing_tax": round(processing_tax, 2),
        "fulfilment_cost": round(fulfilment, 2),
        "return_or_dispute_cost": round(return_cost, 2),
        "total_operational_exposure": round(processing_fee + processing_tax + fulfilment + return_cost, 2),
    }


def analyze(customer, amount, device_id=None, ip_address=None, order_id=None,
            client_status=None, bank_status=None, integrity_status=None):
    f = get_features(customer, amount, device_id, ip_address, order_id)
    c = {}
    reasons = []

    # 1. PAYMENT INTEGRITY / AUTHENTICITY
    integrity = 0
    if integrity_status and str(integrity_status).upper() in {"MISMATCH", "UNCERTAIN"}:
        integrity = 100
        reasons.append("Payment confirmation is inconsistent or uncertain")
    elif client_status and bank_status and str(client_status).upper() != str(bank_status).upper():
        integrity = 100
        reasons.append("Client payment status does not match bank status")
    elif f["integrity_mismatches"] >= 2:
        integrity = 70
        reasons.append("Repeated payment-integrity mismatches in history")
    c["payment_integrity"] = integrity

    # 2. BEHAVIOURAL ANOMALY
    behaviour = 0
    if f["amount_deviation"] >= 5:
        behaviour += 60
        reasons.append("Transaction amount is far outside historical behaviour")
    elif f["amount_deviation"] >= 3:
        behaviour += 45
        reasons.append("Transaction amount is unusually high for this customer")
    elif f["amount_deviation"] >= 1.5:
        behaviour += 25
        reasons.append("Transaction amount differs from normal behaviour")
    if f["failed_transactions"] >= 3:
        behaviour += 20
        reasons.append("Repeated failed payment attempts")
    if f["last_24h"] >= 10:
        behaviour += 15
        reasons.append("Unusually high activity in the last 24 hours")
    c["behavioural_anomaly"] = clamp(behaviour)

    # 3. VELOCITY
    velocity = 0
    if f["last_1m"] >= 5:
        velocity = 100
        reasons.append("Very high transaction velocity in the last minute")
    elif f["last_1m"] >= 3:
        velocity = 80
        reasons.append("High transaction velocity in the last minute")
    elif f["last_10m"] >= 5:
        velocity = 60
        reasons.append("High transaction velocity in the last 10 minutes")
    elif f["last_10m"] >= 3:
        velocity = 35
    c["velocity"] = velocity

    # 4. FRAUD SPIKE / SYSTEM ANOMALY
    spike = 0
    if f["fraud_spike_total"] >= 20 and f["fraud_spike_failure_rate"] >= 0.40:
        spike = 100
        reasons.append("System-wide payment failure spike detected")
    elif f["fraud_spike_total"] >= 10 and f["fraud_spike_failure_rate"] >= 0.30:
        spike = 70
        reasons.append("Abnormal system-wide payment failure rate")
    elif f["fraud_spike_total"] >= 5 and f["fraud_spike_failure_rate"] >= 0.40:
        spike = 45
    c["fraud_spike"] = spike

    # 5. CHARGEBACK RISK
    chargeback = 5
    if f["chargeback_count"] >= 3:
        chargeback += 60
        reasons.append("Repeated chargeback history")
    elif f["chargeback_count"] >= 1:
        chargeback += 35
        reasons.append("Previous chargeback activity")
    if f["chargeback_rate"] >= 0.20:
        chargeback += 25
        reasons.append("High historical chargeback rate")
    elif f["chargeback_rate"] >= 0.10:
        chargeback += 10
    c["chargeback_risk"] = clamp(chargeback)

    # 6. REFUND / RETURN RISK
    refund = 5
    if f["refund_count"] >= 5:
        refund += 55
        reasons.append("Frequent refunds in customer history")
    elif f["refund_count"] >= 2:
        refund += 30
        reasons.append("Repeated refunds in customer history")
    if f["refund_rate"] >= 0.30:
        refund += 30
        reasons.append("High refund rate")
    elif f["refund_rate"] >= 0.15:
        refund += 15
    c["refund_risk"] = clamp(refund)

    # 7. ABUSE RING: many distinct identities linked to device/IP
    ring = 0
    if f["distinct_device_customers"] >= 5:
        ring = 100
        reasons.append("Five or more customer identities are linked to one device")
    elif f["distinct_device_customers"] >= 4:
        ring = 80
        reasons.append("Several customer identities share one device")
    elif f["distinct_device_customers"] >= 2:
        ring = 45
        reasons.append("Device is shared across customer identities")

    if f["distinct_ip_customers"] >= 6:
        ring = max(ring, 90)
        reasons.append("Many customer identities share one IP")
    elif f["distinct_ip_customers"] >= 4:
        ring = max(ring, 65)
        reasons.append("Several customer identities share one IP")
    c["abuse_ring"] = clamp(ring)

    # 8. DUPLICATE PAYMENT
    duplicate = 75 if f["duplicate_count"] >= 1 else 0
    if duplicate:
        reasons.append("Possible duplicate payment for the same customer/amount/order")
    c["duplicate_payment"] = duplicate

    # 9. ADAPTIVE HISTORY / CONTINUOUS LEARNING SIGNAL
    # Small bounded adjustment so legitimate history can reduce friction.
    adaptive = 15
    if f["successful_transactions"] >= 5:
        adaptive -= min(10, f["successful_transactions"])
    if f["chargeback_rate"] >= 0.10:
        adaptive += 20
    if f["refund_rate"] >= 0.20:
        adaptive += 10
    c["adaptive_history"] = clamp(adaptive)

    # 10. FALSE-POSITIVE COST OPTIMIZER / ADAPTIVE THRESHOLDS
    # Higher-value payments are evaluated more cautiously.
    if amount >= 25000:
        verify_threshold, block_threshold = 35, 65
    elif amount >= 10000:
        verify_threshold, block_threshold = 40, 65
    else:
        verify_threshold, block_threshold = 45, 70

    weights = {
        "payment_integrity": 0.18,
        "behavioural_anomaly": 0.16,
        "velocity": 0.12,
        "fraud_spike": 0.14,
        "chargeback_risk": 0.12,
        "refund_risk": 0.08,
        "abuse_ring": 0.12,
        "duplicate_payment": 0.08,
    }

    base_score = sum(c[name] * weight for name, weight in weights.items())
    adaptive_adjustment = (c["adaptive_history"] - 15) * 0.20
    risk_score = clamp(base_score + adaptive_adjustment)

    # Strong evidence can trigger an immediate defense action.
    hard_block = (
        c["payment_integrity"] >= 100
        or c["abuse_ring"] >= 100
        or (c["duplicate_payment"] >= 75 and c["velocity"] >= 60)
    )

    if hard_block or risk_score >= block_threshold:
        decision = "BLOCK"
        level = "HIGH"
        agent = {
            "action": "BLOCK_TRANSACTION",
            "human_review": True,
            "reason": "High merchant-loss risk detected; transaction blocked pending review",
        }
    elif risk_score >= verify_threshold:
        decision = "VERIFY"
        level = "MEDIUM"
        agent = {
            "action": "REQUEST_ADDITIONAL_VERIFICATION",
            "human_review": False,
            "reason": "Suspicious signals detected; additional verification is safer than an immediate block",
        }
    else:
        decision = "APPROVE"
        level = "LOW"
        agent = {
            "action": "ALLOW_TRANSACTION",
            "human_review": False,
            "reason": "Transaction risk is within the acceptable range",
        }

    # Merchant-loss model: payment value at risk + estimated payment/fulfilment exposure.
    costs = merchant_cost_estimate(amount)
    risk_value_at_risk = amount * risk_score / 100.0
    expected_loss = round(risk_value_at_risk + costs["total_operational_exposure"] * (risk_score / 100.0), 2)
    false_positive_cost = round(amount * (0.02 if decision == "BLOCK" else 0.01), 2)
    loss_prevented = round(max(0, expected_loss - false_positive_cost), 2) if decision in {"BLOCK", "VERIFY"} else 0

    return {
        "risk_score": round(risk_score, 2),
        "risk_level": level,
        "decision": decision,
        "expected_loss": expected_loss,
        "false_positive_cost": false_positive_cost,
        "estimated_loss_prevented": loss_prevented,
        "merchant_cost_estimate": costs,
        "components": {k: round(v, 2) for k, v in c.items()},
        "weights": weights,
        "thresholds": {"verify": verify_threshold, "block": block_threshold},
        "explanation": reasons[:12] or ["No material risk signal detected"],
        "agent_action": agent,
        "features": f,
    }


def save_risk(payment_id, customer, amount, result, device_id, ip_address):
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO risk_transactions
            (payment_id, customer, amount, device_id, ip_address,
             risk_score, risk_level, decision, expected_loss,
             components, explanation, agent_action)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            payment_id, customer, amount, device_id, ip_address,
            result["risk_score"], result["risk_level"], result["decision"],
            result["expected_loss"], json.dumps(result["components"]),
            "; ".join(result["explanation"]), result["agent_action"]["action"]
        ))
        cur.execute("""
            INSERT INTO risk_events(payment_id,customer,risk_score,expected_loss,outcome,actual_loss)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (payment_id, customer, result["risk_score"], result["expected_loss"], None, 0))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()


def record_loss(payment_id, customer, loss_type, amount, estimated_cost=0):
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO merchant_loss_events
            (payment_id,customer,loss_type,amount,estimated_cost)
            VALUES (%s,%s,%s,%s,%s)
        """, (payment_id, customer, loss_type, amount, estimated_cost))
        conn.commit()
    finally:
        cur.close()
        conn.close()


def learn_from_outcome(payment_id, customer, outcome, amount):
    actual_loss = amount if outcome in {"refund", "chargeback"} else 0
    conn = db()
    cur = conn.cursor()
    try:
        cur.execute("""
            UPDATE risk_events
            SET outcome=%s, actual_loss=%s
            WHERE event_id=(
                SELECT event_id FROM risk_events
                WHERE payment_id=%s ORDER BY created_at DESC LIMIT 1
            )
        """, (outcome, actual_loss, payment_id))
        cur.execute("""
            INSERT INTO risk_feedback
            (payment_id,customer,predicted_decision,actual_outcome,predicted_risk,actual_loss)
            SELECT %s,%s,
                   (SELECT decision FROM risk_transactions WHERE payment_id=%s ORDER BY transaction_time DESC LIMIT 1),
                   %s,
                   (SELECT risk_score FROM risk_transactions WHERE payment_id=%s ORDER BY transaction_time DESC LIMIT 1),
                   %s
        """, (payment_id, customer, payment_id, outcome, payment_id, actual_loss))
        conn.commit()
    finally:
        cur.close()
        conn.close()
    return actual_loss


def recovery_agent(outcome):
    if outcome == "chargeback":
        return {
            "action": "GENERATE_CHARGEBACK_EVIDENCE",
            "description": "Prepare transaction, verification and fulfilment evidence for dispute response"
        }
    if outcome == "refund":
        return {
            "action": "FLAG_REFUND_FOR_MERCHANT_REVIEW",
            "description": "Record refund and evaluate repeated refund behaviour"
        }
    return {
        "action": "MONITOR",
        "description": "Use the outcome as feedback for future risk decisions"
    }


@app.route("/", methods=["GET"])
def dashboard():
    return render_template_string(DASHBOARD_HTML)


@app.route("/internal-risk-analysis", methods=["POST"])
def internal_risk_analysis():
    data = request.get_json(silent=True) or {}
    customer = str(data.get("customer", "")).strip()
    amount = num(data.get("amount"), -1)
    device_id = data.get("device_id")
    order_id = data.get("order_id")
    client_status = data.get("client_status")
    bank_status = data.get("bank_status")
    integrity_status = data.get("integrity_status")

    if not customer or amount <= 0:
        return jsonify({"error": "customer and positive amount are required"}), 400

    result = analyze(
        customer, amount, device_id, client_ip(), order_id,
        client_status, bank_status, integrity_status
    )
    return jsonify(result)


@app.route("/create-payment", methods=["POST"])
def create_payment():
    data = request.get_json(silent=True) or {}
    customer = str(data.get("customer", "")).strip()
    amount = num(data.get("amount"), -1)
    device_id = data.get("device_id")
    order_id = data.get("order_id")
    client_status = data.get("client_status")
    bank_status = data.get("bank_status")
    simulate_integrity = str(data.get("simulate_integrity", "NONE")).upper()
    ip_address = client_ip()

    if not customer or amount <= 0:
        return jsonify({"error": "customer and positive amount are required"}), 400

    payment_id = str(uuid.uuid4())
    integrity_status = simulate_integrity if simulate_integrity in {"MISMATCH", "UNCERTAIN"} else None

    result = analyze(
        customer, amount, device_id, ip_address, order_id,
        client_status, bank_status, integrity_status
    )

    # Risk decision happens BEFORE bank debit.
    if result["decision"] == "BLOCK":
        status = "BLOCKED"
        message = "Transaction blocked by internal risk engine"
    elif result["decision"] == "VERIFY":
        status = "VERIFY"
        message = "Additional verification required"
    elif integrity_status:
        # Simulates the real-world case where payment state is uncertain.
        status = "FAILED"
        message = "Payment confirmation could not be verified"
    else:
        bank_ok, message = bank_payment(customer, amount)
        status = "SUCCESS" if bank_ok else "FAILED"

    final_integrity = integrity_status or ("MATCH" if status == "SUCCESS" else "UNKNOWN")

    conn = db()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO payments
            (payment_id,amount,customer,status,transaction_time,device_id,ip_address,
             order_id,client_status,bank_status,integrity_status,failure_reason)
            VALUES (%s,%s,%s,%s,CURRENT_TIMESTAMP,%s,%s,%s,%s,%s,%s,%s)
        """, (
            payment_id, amount, customer, status, device_id, ip_address,
            order_id, client_status, bank_status, final_integrity,
            None if status == "SUCCESS" else message
        ))
        conn.commit()
    finally:
        cur.close()
        conn.close()

    save_risk(payment_id, customer, amount, result, device_id, ip_address)

    if result["decision"] in {"BLOCK", "VERIFY"}:
        record_loss(
            payment_id, customer, "RISK_PREVENTION",
            result["expected_loss"], result["estimated_loss_prevented"]
        )
    if integrity_status:
        record_loss(payment_id, customer, "PAYMENT_INTEGRITY", amount, result["expected_loss"])

    return jsonify({
        "payment_id": payment_id,
        "customer": customer,
        "amount": amount,
        "status": status,
        "message": message,
        "risk": {
            "score": result["risk_score"],
            "level": result["risk_level"],
            "decision": result["decision"]
        }
    })


@app.route("/report-outcome", methods=["POST"])
def report_outcome():
    data = request.get_json(silent=True) or {}
    payment_id = str(data.get("payment_id", "")).strip()
    outcome = str(data.get("outcome_type", "")).lower().strip()

    if not payment_id or outcome not in {"refund", "chargeback", "legitimate"}:
        return jsonify({
            "error": "payment_id and outcome_type (refund, chargeback, legitimate) are required"
        }), 400

    conn = db()
    cur = conn.cursor()
    try:
        cur.execute("SELECT customer, amount FROM payments WHERE payment_id=%s", (payment_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "payment not found"}), 404
        customer, amount = row
        cur.execute("""
            INSERT INTO payment_outcomes(payment_id,customer,outcome_type,amount)
            VALUES (%s,%s,%s,%s)
        """, (payment_id, customer, outcome, amount))
        conn.commit()
    finally:
        cur.close()
        conn.close()

    actual_loss = learn_from_outcome(payment_id, customer, outcome, num(amount))
    recovery = recovery_agent(outcome)

    if actual_loss > 0:
        record_loss(payment_id, customer, outcome.upper(), num(amount), num(amount))

    return jsonify({
        "payment_id": payment_id,
        "outcome": outcome,
        "actual_loss": actual_loss,
        "recovery_agent": recovery,
        "learning": "Outcome recorded and fed back into risk history"
    })


@app.route("/transaction-history/<customer>", methods=["GET"])
def transaction_history(customer):
    conn = db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT payment_id,amount,status,transaction_time,device_id,ip_address,
                   order_id,integrity_status
            FROM payments WHERE customer=%s ORDER BY transaction_time DESC
        """, (customer,))
        return jsonify(cur.fetchall())
    finally:
        cur.close()
        conn.close()


@app.route("/api/risk-dashboard", methods=["GET"])
def risk_dashboard():
    conn = db()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute("""
            SELECT COUNT(*) AS total,
                   COUNT(*) FILTER (WHERE status IN ('SUCCESS','CAPTURED','AUTHORIZED')) AS successful,
                   COUNT(*) FILTER (WHERE status='BLOCKED') AS blocked,
                   COUNT(*) FILTER (WHERE status='VERIFY') AS verification,
                   COUNT(*) FILTER (WHERE status='FAILED') AS failed,
                   COALESCE(SUM(amount),0) AS total_value
            FROM payments
        """)
        summary = cur.fetchone()

        cur.execute("SELECT COALESCE(SUM(expected_loss),0) AS value FROM risk_transactions")
        expected_loss = num(cur.fetchone()["value"])
        cur.execute("SELECT COALESCE(SUM(actual_loss),0) AS value FROM risk_events")
        actual_loss = num(cur.fetchone()["value"])
        cur.execute("SELECT COALESCE(SUM(estimated_cost),0) AS value FROM merchant_loss_events WHERE loss_type='RISK_PREVENTION'")
        recorded_prevented = num(cur.fetchone()["value"])

        cur.execute("""
            SELECT payment_id,customer,amount,status,transaction_time,device_id,
                   ip_address,order_id,integrity_status
            FROM payments ORDER BY transaction_time DESC LIMIT 25
        """)
        transactions = cur.fetchall()

        cur.execute("""
            SELECT payment_id,customer,risk_score,risk_level,decision,expected_loss,
                   components,explanation,agent_action,transaction_time
            FROM risk_transactions ORDER BY transaction_time DESC LIMIT 25
        """)
        risk_rows = cur.fetchall()

        return jsonify({
            "summary": {
                "total_transactions": int(summary["total"] or 0),
                "successful": int(summary["successful"] or 0),
                "blocked": int(summary["blocked"] or 0),
                "verification": int(summary["verification"] or 0),
                "failed": int(summary["failed"] or 0),
                "total_value": round(num(summary["total_value"]), 2),
                "expected_loss": round(expected_loss, 2),
                "actual_loss": round(actual_loss, 2),
                "estimated_loss_prevented": round(max(recorded_prevented, expected_loss - actual_loss), 2),
            },
            "recent_transactions": transactions,
            "recent_risk": risk_rows,
        })
    finally:
        cur.close()
        conn.close()


@app.route("/api/reset-demo", methods=["POST"])
def reset_demo():
    conn = db()
    cur = conn.cursor()
    try:
        for table in [
            "risk_feedback", "merchant_loss_events", "payment_outcomes",
            "risk_events", "risk_transactions", "payments"
        ]:
            cur.execute(f"DELETE FROM {table}")
        cur.execute("UPDATE bank_accounts SET balance=50000 WHERE customer='Vaishnavi'")
        conn.commit()
        return jsonify({"message": "Demo transaction and risk data reset"})
    finally:
        cur.close()
        conn.close()


DASHBOARD_HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Merchant Loss Prevention AI</title>
<style>
*{box-sizing:border-box}body{margin:0;background:#f4f6fa;color:#18202a;font-family:Inter,Segoe UI,Arial,sans-serif}.wrap{max-width:1250px;margin:auto;padding:24px}.top{display:flex;justify-content:space-between;align-items:center;gap:16px}.brand h1{margin:0;font-size:30px}.brand p{margin:6px 0;color:#6b7280}.online{padding:8px 12px;border-radius:20px;background:#e8f7ee;color:#18733a;font-weight:800;font-size:13px}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:22px 0}.card{background:#fff;border:1px solid #e5e8ee;border-radius:16px;padding:18px;box-shadow:0 5px 20px rgba(20,30,50,.05)}.label{font-size:13px;color:#6b7280}.kpi{font-size:29px;font-weight:900;margin-top:8px}.main{display:grid;grid-template-columns:1.1fr .9fr;gap:16px}.row{display:grid;grid-template-columns:1fr 1fr;gap:10px}.field label{font-size:13px;font-weight:800}.input{width:100%;padding:11px;margin:6px 0 12px;border:1px solid #d7dce5;border-radius:10px;background:#fff}.buttons{display:flex;flex-wrap:wrap;gap:8px}.btn{border:0;border-radius:10px;padding:11px 15px;font-weight:800;cursor:pointer;background:#18202a;color:#fff}.btn.alt{background:#edf0f4;color:#18202a}.result{display:none;margin-top:16px;padding:17px;border-radius:14px}.result.low{background:#eaf8ef}.result.medium{background:#fff7df}.result.high{background:#ffe8e8}.score{font-size:44px;font-weight:900}.decision{display:inline-block;padding:6px 10px;border-radius:20px;font-weight:900;font-size:12px;background:#fff;margin-top:6px}.reason{margin:6px 0}.signal{margin:11px 0}.signaltop{display:flex;justify-content:space-between}.bar{height:8px;background:#e9edf2;border-radius:10px;overflow:hidden}.fill{height:100%;background:#18202a}.tablewrap{overflow:auto}.table{width:100%;border-collapse:collapse;font-size:13px}.table th,.table td{text-align:left;padding:10px;border-bottom:1px solid #edf0f4;white-space:nowrap}.small{font-size:12px;color:#6b7280}@media(max-width:900px){.grid{grid-template-columns:1fr 1fr}.main{grid-template-columns:1fr}}@media(max-width:600px){.grid{grid-template-columns:1fr}.row{grid-template-columns:1fr}.wrap{padding:14px}.top{align-items:flex-start;flex-direction:column}}
</style>
</head>
<body>
<div class="wrap">
<div class="top">
<div class="brand"><h1>Merchant Loss Prevention AI</h1><p>Internal risk layer for fraud, refunds, chargebacks, abuse and payment integrity</p></div>
<div class="online">● RISK ENGINE ONLINE</div>
</div>

<div class="grid">
<div class="card"><div class="label">Transactions</div><div class="kpi" id="total">0</div></div>
<div class="card"><div class="label">Blocked</div><div class="kpi" id="blocked">0</div></div>
<div class="card"><div class="label">Expected Merchant Loss</div><div class="kpi" id="expected">₹0</div></div>
<div class="card"><div class="label">Estimated Loss Prevented</div><div class="kpi" id="prevented">₹0</div></div>
</div>

<div class="main">
<div class="card">
<h2>Live Transaction Analyzer</h2>
<div class="row">
<div class="field"><label>Customer</label><input id="customer" class="input" value="Vaishnavi"></div>
<div class="field"><label>Amount (₹)</label><input id="amount" class="input" type="number" value="1000"></div>
</div>
<div class="row">
<div class="field"><label>Device ID</label><input id="device" class="input" value="DEV001"></div>
<div class="field"><label>Order ID</label><input id="order" class="input" value="ORDER001"></div>
</div>
<div class="buttons">
<button class="btn" onclick="analyzeRisk()">Analyze Risk</button>
<button class="btn alt" onclick="processPayment()">Process Payment</button>
<button class="btn alt" onclick="simulateMismatch()">Simulate Payment Mismatch</button>
<button class="btn alt" onclick="resetDemo()">Reset Demo</button>
</div>
<div id="result" class="result">
<div class="score" id="score">0/100</div>
<div class="decision" id="decision">APPROVE</div>
<p id="loss"></p>
<h3>Explainable Risk Signals</h3>
<ul id="reasons"></ul>
<div id="signals"></div>
<p id="agent" class="small"></p>
</div>
</div>

<div class="card">
<h2>Risk Intelligence</h2>
<p class="small">The engine combines transaction, customer-history and network-level signals.</p>
<div id="intelligence"><p class="small">Analyze a transaction to populate the risk signals.</p></div>
</div>
</div>

<div class="card" style="margin-top:16px">
<h2>Live Transaction Feed</h2>
<div class="tablewrap"><table class="table"><thead><tr><th>Time</th><th>Customer</th><th>Amount</th><th>Status</th><th>Device</th><th>Integrity</th></tr></thead><tbody id="tx"></tbody></table></div>
</div>
</div>

<script>
const $=id=>document.getElementById(id);
const money=n=>'₹'+Number(n||0).toLocaleString('en-IN',{maximumFractionDigits:2});
async function api(url,options={}){const r=await fetch(url,options);return await r.json();}
async function analyzeRisk(){
 const body={customer:$('customer').value,amount:Number($('amount').value),device_id:$('device').value,order_id:$('order').value};
 const d=await api('/internal-risk-analysis',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 if(d.error){alert(d.error);return} showResult(d);
}
async function processPayment(){
 const body={customer:$('customer').value,amount:Number($('amount').value),device_id:$('device').value,order_id:$('order').value};
 const d=await api('/create-payment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 if(d.error){alert(d.error);return}
 const risk=d.risk||{};
 showResult({risk_score:risk.score||0,risk_level:risk.level||'LOW',decision:risk.decision||d.status,expected_loss:0,estimated_loss_prevented:0,explanation:[d.message],components:{},agent_action:{action:d.status,reason:d.message}});load();
}
async function simulateMismatch(){
 const body={customer:$('customer').value,amount:Number($('amount').value),device_id:$('device').value,order_id:$('order').value,simulate_integrity:'MISMATCH'};
 const d=await api('/create-payment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 if(d.error){alert(d.error);return}
 const risk=d.risk||{};
 showResult({risk_score:risk.score||100,risk_level:risk.level||'HIGH',decision:risk.decision||'BLOCK',expected_loss:0,estimated_loss_prevented:0,explanation:[d.message,'Client/bank payment state mismatch simulated'],components:{payment_integrity:100},agent_action:{action:'BLOCK_TRANSACTION',reason:d.message}});load();
}
function showResult(d){
 const level=d.risk_level||'LOW';$('result').style.display='block';$('result').className='result '+level.toLowerCase();
 $('score').textContent=Number(d.risk_score||0).toFixed(1)+'/100';$('decision').textContent=d.decision||'UNKNOWN';
 $('loss').textContent='Expected merchant loss: '+money(d.expected_loss)+' • Estimated loss prevented: '+money(d.estimated_loss_prevented||0);
 $('reasons').innerHTML=(d.explanation||[]).map(x=>'<li class="reason">'+x+'</li>').join('');
 $('agent').textContent='Agent action: '+(d.agent_action?.action||'MONITOR')+' • '+(d.agent_action?.reason||'');
 $('intelligence').innerHTML=Object.entries(d.components||{}).map(([k,v])=>'<div class="signal"><div class="signaltop"><span>'+k.replaceAll('_',' ')+'</span><b>'+Number(v).toFixed(0)+'/100</b></div><div class="bar"><div class="fill" style="width:'+Math.min(100,Number(v))+'%"></div></div></div>').join('')||'<p class="small">No component data.</p>';
}
async function load(){
 const d=await api('/api/risk-dashboard');const s=d.summary||{};
 $('total').textContent=s.total_transactions||0;$('blocked').textContent=s.blocked||0;$('expected').textContent=money(s.expected_loss);$('prevented').textContent=money(s.estimated_loss_prevented);
 $('tx').innerHTML=(d.recent_transactions||[]).map(r=>'<tr><td>'+new Date(r.transaction_time).toLocaleString()+'</td><td>'+r.customer+'</td><td>'+money(r.amount)+'</td><td>'+r.status+'</td><td>'+(r.device_id||'-')+'</td><td>'+(r.integrity_status||'-')+'</td></tr>').join('');
}
async function resetDemo(){if(confirm('Reset demo transactions, outcomes and risk history?')){await api('/api/reset-demo',{method:'POST'});load();}}
load();setInterval(load,5000);
</script>
</body></html>'''


if __name__ == "__main__":
    initialize_database()
    app.run(debug=True)
