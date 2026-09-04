import csv
import random

N = 10000
OUTPUT = "synthetic_10k.csv"

random.seed(42)

SIGNALS = [
    "payment_integrity",
    "behavioural_anomaly",
    "velocity",
    "fraud_spike",
    "chargeback_risk",
    "refund_return_risk",
    "abuse_ring",
    "duplicate_payment",
]

WEIGHTS = {
    "payment_integrity": 0.18,
    "behavioural_anomaly": 0.16,
    "velocity": 0.14,
    "fraud_spike": 0.12,
    "chargeback_risk": 0.12,
    "refund_return_risk": 0.10,
    "abuse_ring": 0.10,
    "duplicate_payment": 0.08,
}

# Target score bands
BANDS = [
    ("normal", 55, 0, 29),
    ("behavioural_anomaly", 7, 30, 54),
    ("velocity_attack", 6, 30, 54),
    ("fraud_spike", 6, 55, 74),
    ("chargeback_risk", 6, 55, 74),
    ("refund_abuse", 5, 30, 54),
    ("abuse_ring", 5, 55, 74),
    ("duplicate_payment", 4, 30, 54),
    ("integrity_issue", 3, 55, 74),
    ("mixed_attack", 3, 75, 95),
]

PRIMARY = {
    "behavioural_anomaly": "behavioural_anomaly",
    "velocity_attack": "velocity",
    "fraud_spike": "fraud_spike",
    "chargeback_risk": "chargeback_risk",
    "refund_abuse": "refund_return_risk",
    "abuse_ring": "abuse_ring",
    "duplicate_payment": "duplicate_payment",
    "integrity_issue": "payment_integrity",
    "mixed_attack": None,
}


def score(v):
    return sum(v[k] * WEIGHTS[k] for k in SIGNALS)


def make_values(scenario, target):
    primary = PRIMARY.get(scenario)

    for _ in range(1000):

        # Start all signals around the target risk level.
        values = {}

        for s in SIGNALS:
            values[s] = max(
                0,
                min(100, target + random.uniform(-12, 12))
            )

        # Make the main attack signal stronger.
        if primary:
            values[primary] = max(
                values[primary],
                target + random.uniform(10, 25)
            )

        # Mixed attack = several simultaneous elevated signals.
        if scenario == "mixed_attack":
            for s in SIGNALS:
                values[s] = max(
                    values[s],
                    target + random.uniform(5, 18)
                )

        actual_score = score(values)

        # Accept only values that actually land in the
        # intended production decision band.
        if target < 30 and actual_score < 30:
            return values

        if 30 <= target < 55 and 30 <= actual_score < 55:
            return values

        if 55 <= target < 75 and 55 <= actual_score < 75:
            return values

        if target >= 75 and actual_score >= 75:
            return values

    # Fallback
    return {s: target for s in SIGNALS}


def main():

    fieldnames = [
        "transaction_id",
        "amount",
        "scenario",
        *SIGNALS,
        "ground_truth_risky",
    ]

    counts = {}

    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:

        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        scenario_names = [x[0] for x in BANDS]
        weights = [x[1] for x in BANDS]

        for i in range(1, N + 1):

            scenario = random.choices(
                scenario_names,
                weights=weights,
                k=1
            )[0]

            band = next(x for x in BANDS if x[0] == scenario)
            low = band[2]
            high = band[3]

            target = random.uniform(low, high)

            values = make_values(scenario, target)

            # Normal = legitimate.
            # All attack scenarios = risky.
            risky = 0 if scenario == "normal" else 1

            # Small label noise.
            if random.random() < 0.02:
                risky = 1 - risky

            amount = round(random.uniform(100, 50000), 2)

            row = {
                "transaction_id": f"TXN{i:05d}",
                "amount": amount,
                "scenario": scenario,
                "ground_truth_risky": risky,
            }

            for s in SIGNALS:
                row[s] = round(values[s], 2)

            writer.writerow(row)

            counts[scenario] = counts.get(scenario, 0) + 1

    print("=" * 60)
    print("PAYSHIELD 10K DATASET CREATED")
    print("=" * 60)
    print(f"Transactions: {N:,}")
    print()

    for scenario, count in counts.items():
        print(f"{scenario:<22} {count:>5}")

    print()
    print(f"Saved: {OUTPUT}")
    print("=" * 60)


if __name__ == "__main__":
    main()