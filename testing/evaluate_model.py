import csv
import os

INPUT = "synthetic_10k.csv"
OUT = "results/evaluation_report.txt"

WEIGHTS = {
    "payment_integrity": 0.18,
    "behavioural_anomaly": 0.16,
    "velocity": 0.14,
    "fraud_spike": 0.12,
    "chargeback_risk": 0.12,
    "refund_return_risk": 0.10,
    "abuse_ring": 0.10,
    "duplicate_payment": 0.08
}

def risk_score(r):
    return round(sum(float(r[k]) * w for k, w in WEIGHTS.items()), 2)

def decision(s):
    if s < 30:
        return "ALLOW"
    if s < 55:
        return "VERIFY"
    if s < 75:
        return "REVIEW"
    return "BLOCK"

with open(INPUT, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

tp = tn = fp = fn = 0
decisions = {"ALLOW":0, "VERIFY":0, "REVIEW":0, "BLOCK":0}

loss_without = 0
loss_with = 0
prevented = 0
fp_cost = 0

scenario = {}

for r in rows:
    score = risk_score(r)
    d = decision(score)

    decisions[d] += 1

    actual = int(r["ground_truth_risky"])
    predicted = 0 if d == "ALLOW" else 1

    if actual == 1 and predicted == 1:
        tp += 1
    elif actual == 0 and predicted == 0:
        tn += 1
    elif actual == 0 and predicted == 1:
        fp += 1
    else:
        fn += 1

    amount = float(r["amount"])
    potential = amount * 0.10 + 150

    if actual:
        loss_without += potential

        if d == "BLOCK":
            prevented += potential
            loss_with += 0
        elif d == "REVIEW":
            prevented += potential * 0.75
            loss_with += potential * 0.25
        elif d == "VERIFY":
            prevented += potential * 0.50
            loss_with += potential * 0.50
        else:
            loss_with += potential

    elif predicted:
        cost = amount * 0.02
        fp_cost += cost
        loss_with += cost

    s = r["scenario"]

    if s not in scenario:
        scenario[s] = [0, 0, 0]

    scenario[s][0] += 1
    scenario[s][1] += score

    if predicted:
        scenario[s][2] += 1

total = len(rows)

accuracy = (tp + tn) / total
precision = tp / (tp + fp) if tp + fp else 0
recall = tp / (tp + fn) if tp + fn else 0
f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0
fpr = fp / (fp + tn) if fp + tn else 0
fnr = fn / (fn + tp) if fn + tp else 0

prevention = prevented / loss_without if loss_without else 0

report = []

report.append("=" * 65)
report.append("PAYSHIELD AI — 10,000 TRANSACTION EVALUATION")
report.append("=" * 65)

report.append("")
report.append("DECISION DISTRIBUTION")
report.append("-" * 65)

for d in decisions:
    report.append(
        f"{d:<10}: {decisions[d]:>5} "
        f"({decisions[d]/total*100:.2f}%)"
    )

report.append("")
report.append("MODEL PERFORMANCE")
report.append("-" * 65)
report.append(f"Accuracy            : {accuracy*100:.2f}%")
report.append(f"Precision           : {precision*100:.2f}%")
report.append(f"Recall              : {recall*100:.2f}%")
report.append(f"F1 Score            : {f1*100:.2f}%")
report.append(f"False Positive Rate : {fpr*100:.2f}%")
report.append(f"False Negative Rate : {fnr*100:.2f}%")

report.append("")
report.append("CONFUSION MATRIX")
report.append("-" * 65)
report.append(f"True Positives  : {tp}")
report.append(f"True Negatives  : {tn}")
report.append(f"False Positives : {fp}")
report.append(f"False Negatives : {fn}")

report.append("")
report.append("SCENARIO DETECTION")
report.append("-" * 65)

for s, x in sorted(scenario.items()):
    count, score_sum, interventions = x
    report.append(
        f"{s:<22} "
        f"n={count:>4} "
        f"avg_score={score_sum/count:>6.2f} "
        f"intervention={interventions/count*100:>6.2f}%"
    )

report.append("")
report.append("MERCHANT LOSS SIMULATION")
report.append("-" * 65)
report.append(f"Loss without AI : ₹{loss_without:,.2f}")
report.append(f"Loss with AI    : ₹{loss_with:,.2f}")
report.append(f"Loss prevented  : ₹{prevented:,.2f}")
report.append(f"FP cost         : ₹{fp_cost:,.2f}")
report.append(f"Prevention rate : {prevention*100:.2f}%")

report.append("")
report.append("NOTE")
report.append("-" * 65)
report.append(
    "Synthetic benchmark using PayShield's production risk weights "
    "and decision thresholds."
)
report.append(
    "Merchant-loss figures are prototype simulation estimates, "
    "not real financial results."
)

text = "\n".join(report)

os.makedirs("results", exist_ok=True)

with open(OUT, "w", encoding="utf-8") as f:
    f.write(text)

print(text)
print("")
print("REPORT SAVED:", OUT)