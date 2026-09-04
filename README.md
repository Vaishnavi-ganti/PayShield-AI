# PayShield AI

### Intelligent Merchant Loss Prevention & Payment Risk Management

> **Protect every payment. Prevent every avoidable loss.**

PayShield AI is an intelligent risk-management layer built on top of a simulated payment gateway. It is designed to help merchants prevent avoidable financial losses caused by fraud, payment inconsistencies, chargebacks, refund abuse, duplicate payments, abnormal transaction behaviour, and coordinated abuse.

The project was developed for the **Razorpay AI Buildathon — Track 02: AI Risk Manager**.

---

## 🚀 The Problem

Payment fraud is only one part of the problem faced by merchants.

A merchant can lose money because of:

- Fraudulent transactions
- Chargebacks
- Refund and return abuse
- Duplicate payments
- Payment gateway/bank inconsistencies
- Failed-but-debited payments
- Abnormally high transaction velocity
- Coordinated abuse across multiple identities
- Fraud spikes
- Operational and recovery costs

Traditional payment systems often focus primarily on one question:

> **"Should this transaction be approved?"**

But merchants need a broader answer:

> **"What risk does this transaction create, how much could it cost the merchant, and what is the best action to minimize that loss?"**

PayShield AI is designed around this problem.

---

# 💡 Our Solution

PayShield AI acts as an intelligent risk-management layer between the payment gateway and the merchant's decision process.

Instead of relying on a simple approve/decline mechanism, PayShield:

1. Validates payment integrity
2. Extracts transaction and behavioural signals
3. Calculates a real-time risk score
4. Estimates potential merchant loss
5. Determines the least-friction response
6. Explains why the decision was made
7. Initiates appropriate recovery actions
8. Records the actual outcome
9. Uses historical outcomes as feedback for future improvement
10. Provides merchants with risk and loss-prevention analytics

The central principle is:

> **Maximum fraud prevention with minimum customer friction.**

---

# 🧠 How PayShield AI Works

The complete system follows this lifecycle:

```text
Customer
   ↓
Payment Gateway
   ↓
Payment Validation
   ↓
Simulated Bank Authorization
   ↓
Transaction Ledger
   ↓
PayShield AI Risk Engine
   ↓
Risk Score + Explanation
   ↓
Decision Engine
   ↓
ALLOW / VERIFY / REVIEW / BLOCK
   ↓
Outcome Monitoring
   ↓
Recovery
   ↓
Learning
   ↓
Merchant Analytics

1. Payment Initiation

The customer initiates a payment through the simulated payment gateway.

The gateway validates the transaction and prepares it for authorization.

The transaction is recorded in the payment system and passed through PayShield's risk layer.

2. Payment Integrity Verification

PayShield checks whether the payment state reported by the gateway matches the simulated bank state.

This helps detect situations such as:

Gateway reports success but bank authorization fails
Customer is debited but the merchant does not receive confirmation
Unknown or delayed authorization
Gateway and bank status mismatch
Repeated payment attempts
Failed payment with uncertain final state

This prevents an uncertain payment from being incorrectly treated as a successful transaction.

3. Feature Extraction

PayShield evaluates multiple signals instead of depending on a single fraud indicator.

The current risk engine uses eight major signals:

Risk Signal	What It Detects
Payment Integrity	Gateway/bank inconsistencies
Behavioural Anomaly	Unusual customer behaviour
Velocity	Excessive transaction or payment attempts
Fraud Spike	Sudden increase in suspicious activity
Chargeback Risk	Patterns associated with chargeback-related loss
Refund/Return Risk	Abnormal refund or return behaviour
Abuse Ring	Coordinated activity across identities/devices/IPs
Duplicate Payment	Repeated or duplicate transaction attempts
🧠 Risk Scoring Engine

The eight risk signals are combined into a normalized score from 0 to 100.

The current prototype uses the following weighted model:

Risk Signal	Weight
Payment Integrity	18%
Behavioural Anomaly	16%
Velocity	14%
Fraud Spike	12%
Chargeback Risk	12%
Refund/Return Risk	10%
Abuse Ring	10%
Duplicate Payment	8%

The resulting score represents the risk associated with the transaction.

It does not permanently label a customer as fraudulent.

🎯 Decision Engine

The risk score determines the appropriate action.

Risk Score	Decision	Action
0–29	ALLOW	Process normally
30–54	VERIFY	Request additional verification
55–74	REVIEW	Flag for merchant/risk review
75–100	BLOCK	Stop the high-risk transaction

The objective is not to block every suspicious transaction.

Instead, PayShield uses progressive intervention:

LOW RISK
   ↓
ALLOW

MODERATE RISK
   ↓
VERIFY

HIGH RISK
   ↓
REVIEW

VERY HIGH RISK
   ↓
BLOCK

This helps balance fraud prevention with customer experience.

💰 Expected Merchant Loss

PayShield goes beyond simply asking whether a transaction is risky.

It also estimates:

"How much could this transaction potentially cost the merchant?"

The prototype loss model considers factors such as:

Payment processing fees
GST on processing fees
Potential fulfilment cost
Potential chargeback cost
Potential refund cost
Estimated probability of risk materialization

This connects the risk engine directly to merchant economics.

The loss model is configurable and is intended as a prototype simulation rather than a production financial forecasting model.

🔍 Explainable Risk Analysis

A risk score alone is not sufficient for a merchant.

PayShield therefore shows the major factors contributing to a transaction's risk.

Example:

Risk Score: 82/100
Decision: BLOCK

Major Risk Contributors:

• High transaction velocity
• Duplicate payment attempt
• Abnormal transaction amount
• Fraud-spike activity

This makes the system easier to:

Understand
Audit
Debug
Monitor
Act upon
🤖 Agentic Risk Response

PayShield follows an agentic lifecycle:

DETECT
   ↓
ASSESS
   ↓
DECIDE
   ↓
ACT
   ↓
OBSERVE OUTCOME
   ↓
RECOVER
   ↓
LEARN
DETECT

Identify suspicious transaction-level or merchant-level behaviour.

ASSESS

Combine multiple signals and calculate the risk level.

DECIDE

Determine the appropriate intervention.

ACT

Apply the selected action:

Allow
Verify
Review
Block
Monitor
OBSERVE

Record the actual outcome of the transaction.

RECOVER

Initiate appropriate recovery workflows when a loss event occurs.

LEARN

Use historical outcomes as feedback for improving future risk decisions.

🛡️ Recovery Agent

PayShield continues operating after the initial transaction decision.

When a loss-related event occurs, the recovery layer can initiate an appropriate action.

Chargeback
Chargeback Detected
        ↓
Transaction Analysis
        ↓
Evidence Generation
        ↓
Recovery Action
        ↓
Outcome Monitoring
Refund
Refund Behaviour Detected
        ↓
Risk Assessment
        ↓
Merchant Review Flag
        ↓
Recovery / Monitoring

This extends PayShield beyond fraud prevention into complete merchant loss management.

👥 Abuse-Ring Detection

Some attacks are coordinated rather than isolated.

PayShield can analyze relationships between:

Customers
Devices
IP addresses
Transaction behaviour
Payment attempts

For example:

Customer A ─┐
Customer B ─┼── Shared Device/IP
Customer C ─┤
Customer D ─┘
             ↓
      Suspicious Cluster

Multiple customer identities repeatedly sharing the same device or IP can become a strong abuse signal.

A single legitimate customer using multiple devices is not automatically considered suspicious.

⚡ Fraud-Spike Detection

PayShield also looks beyond individual transactions.

A sudden increase in suspicious activity can indicate an ongoing attack.

Normal Activity
████████████

       ↓

Fraud Spike
████████████████████████

The fraud-spike signal therefore adds merchant-level context to individual transaction risk.

🔁 Refund & Return Risk

Refund behaviour can create substantial merchant losses.

PayShield evaluates signals such as:

Refund frequency
Refund history
Timing of refunds
Repeated refund patterns
Abnormal return behaviour

The objective is not to block legitimate refunds.

Instead, the system identifies unusual patterns that deserve additional merchant attention.

💳 Duplicate Payment Detection

Repeated payment attempts can result in:

Duplicate charges
Customer disputes
Refund processing
Operational overhead
Merchant losses

PayShield detects suspicious repeated attempts and incorporates duplicate-payment risk into the overall transaction score.

🧩 What Technologies Does PayShield Use?
Backend
Python
Flask
REST APIs
Custom risk-scoring engine
Agent-based decision and recovery logic
Database
PostgreSQL

The database stores:

Bank accounts
Payments
Risk transactions
Risk events
Risk feedback
Payment outcomes
Recovery actions
Merchant loss events
Evaluation transactions
Frontend
HTML5
CSS3
JavaScript

The frontend communicates with the Flask backend through REST APIs.

Development & Testing
Visual Studio Code
Postman
pgAdmin
Git
GitHub
Python Virtual Environment
🏗️ System Architecture
                         CUSTOMER
                            │
                            ▼
                  ┌──────────────────┐
                  │ Payment Gateway  │
                  └────────┬─────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │ Payment          │
                  │ Validation       │
                  └────────┬─────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │ Simulated Bank   │
                  │ Authorization    │
                  └────────┬─────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │ Payment Ledger   │
                  └────────┬─────────┘
                           │
                           ▼
              ┌───────────────────────────┐
              │        PAYSHIELD AI       │
              │                           │
              │  Feature Extraction       │
              │          ↓                │
              │  Risk Assessment          │
              │          ↓                │
              │  Expected Loss            │
              │          ↓                │
              │  Explainability           │
              └────────────┬──────────────┘
                           │
                           ▼
                  ┌──────────────────┐
                  │ Decision Engine  │
                  └────────┬─────────┘
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼              ▼
          ALLOW          VERIFY         REVIEW         BLOCK
            │              │              │              │
            └──────────────┴──────────────┴──────────────┘
                                   │
                                   ▼
                         Outcome Monitoring
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
               Recovery                       Learning
                    │                             │
                    └──────────────┬──────────────┘
                                   ▼
                         Merchant Analytics
🗄️ Database Architecture

PostgreSQL maintains the complete payment and risk lifecycle.

                    PostgreSQL
                        │
        ┌───────────────┼────────────────┐
        │               │                │
        ▼               ▼                ▼
     Payments      Risk Engine       Bank Accounts
        │               │
        │        ┌──────┴──────┐
        │        ▼             ▼
        │    Risk Events   Risk Feedback
        │
        ▼
 Payment Outcomes
        │
        ▼
 Recovery Actions
        │
        ▼
 Merchant Loss Events

This allows PayShield to connect a payment with its:

Risk assessment
Decision
Outcome
Recovery action
Financial impact
📡 API Architecture

The Flask backend exposes REST APIs for payment processing and risk management.

Endpoint	Purpose
/create-payment	Create and risk-screen a payment
/report-outcome	Record transaction outcome
/transaction-history/<customer>	Retrieve customer transaction history
/api/risk-dashboard	Retrieve merchant risk analytics
/api/reset-demo	Reset demo data
📊 Merchant Risk Dashboard

The dashboard provides a centralized view of merchant risk.

It tracks:

Total transactions
Successful payments
Blocked payments
Verification requests
Failed payments
Transaction value
Expected merchant loss
Actual loss
Estimated loss prevented
Recent risk activity

This converts transaction data into actionable merchant intelligence.

🧪 Synthetic Evaluation

PayShield was evaluated independently using a separate testing environment.

The benchmark contains:

10,000 synthetic transactions

The dataset includes multiple scenarios:

Normal transactions
Behavioural anomalies
Velocity attacks
Fraud spikes
Chargeback risk
Refund abuse
Abuse rings
Duplicate payments
Payment-integrity issues
Mixed attacks

No real customer payment information or real money is used.

📈 Evaluation Results

Using PayShield's production risk weights and decision thresholds:

Metric	Result
Accuracy	97.94%
Precision	97.88%
Recall	97.58%
F1 Score	97.73%
False Positive Rate	1.76%
False Negative Rate	2.42%
Confusion Matrix
True Positives  : 4436
True Negatives  : 5358
False Positives :   96
False Negatives :  110
💰 Merchant Loss Simulation

The synthetic benchmark also included a prototype merchant-loss simulation.

Loss without AI : ₹11,947,885.13
Loss with AI    : ₹4,345,765.36
Loss prevented  : ₹7,649,340.87

Prevention Rate : 64.02%
Key Result

On a 10,000-transaction synthetic benchmark, PayShield achieved 97.94% accuracy and 97.58% recall while reducing simulated merchant loss by 64.02%.

Important: These are synthetic benchmark and prototype simulation results. They are not claims of actual Razorpay or real-world merchant savings.

### Reproducible Testing

The complete synthetic evaluation environment is available in the
[`testing/`](./testing/) directory.

It includes:
- `generate_dataset.py` — generates the 10,000 synthetic transactions
- `evaluate_model.py` — evaluates the PayShield risk engine
- `synthetic_10k.csv` — synthetic benchmark dataset
- `results/evaluation_report.txt` — complete evaluation report

The benchmark uses the same risk weights and decision thresholds as
the PayShield production risk engine.


⭐ 15 Core Capabilities

PayShield's architecture covers 15 major capabilities:

Real-Time Risk Score
Merchant Loss Prediction
Behavioural Anomaly Detection
Velocity Attack Detection
Fraud-Spike Detection
Chargeback-Risk Prediction
Return/Refund Risk Prediction
Abuse-Ring Detection
Adaptive Decision Engine
Explainable AI
Agentic Risk Response
Recovery Agent
Continuous Learning
False-Positive Cost Optimization
Risk Dashboard & Analytics

These capabilities are not all independent ML models.

The first eight primarily generate risk signals, while the remaining capabilities form the decision, explanation, action, recovery, learning, optimization, and analytics layers.

🎯 Five Key Differentiators
1. Expected Merchant Loss

Connects transaction risk with potential financial impact.

2. Behavioural Intelligence

Looks at behaviour, velocity, history, device/IP relationships, and abnormal patterns.

3. Agentic Risk Response

Uses a complete:

Detect → Assess → Decide → Act → Observe → Recover → Learn

workflow.

4. Minimum-Friction Decision Making

Uses progressive intervention:

ALLOW → VERIFY → REVIEW → BLOCK

instead of blindly blocking suspicious transactions.

5. Measurable Loss Prevention

Measures:

Accuracy
Precision
Recall
F1
False positives
False negatives
Expected loss
Actual loss
Simulated loss prevented
🖥️ Screenshots
Merchant Risk Dashboard

Risk Analysis

Transaction Analysis

Loss Prevention

🔐 Security & Privacy

The prototype follows basic secure-development practices.

PostgreSQL credentials are stored using environment variables.
.env files are excluded from Git.
Virtual environments are excluded from Git.
No real payment credentials are required.
No real money is processed.
Synthetic data is used for evaluation.
Customer risk is evaluated at the transaction level rather than permanently labeling individuals as fraudulent.
🛠️ Running the Project Locally
1. Clone the repository
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd PayShield
2. Create a virtual environment
Windows
python -m venv venv
.\venv\Scripts\Activate.ps1
3. Install dependencies
pip install -r requirements.txt
4. Configure environment variables

Create a .env file in the project root:

DB_PASSWORD=YOUR_POSTGRES_PASSWORD

Configure the PostgreSQL database according to the application settings.

5. Start the application
python app.py

Open the local Flask address displayed in the terminal.

🧪 Testing Environment

The synthetic evaluation environment is maintained separately from the main application.

payshield-testing/
├── generate_dataset.py
├── _make_dataset.py
├── evaluate_model.py
├── synthetic_10k.csv
└── results/
    └── evaluation_report.txt

This keeps the production/demo application clean while allowing the risk engine to be evaluated independently.

📁 Project Structure
PayShield/
│
├── app.py
├── requirements.txt
├── .gitignore
│
├── templates/
│   ├── index.html
│   └── static/
│       ├── app.js
│       └── style.css
│
└── screenshots/
    ├── dashboard.png
    ├── risk_analysis.png
    ├── transaction_analysis.png
    └── loss_prevention.png

The synthetic evaluation environment is maintained separately from the main repository.

🔮 Future Scope

Future versions of PayShield could include:

ML-based fraud classification
Graph neural networks for abuse-ring detection
Real-time streaming risk analysis
Merchant-specific adaptive thresholds
Automated model retraining
Advanced behavioural profiling
Real payment-provider integrations
Automated chargeback evidence generation
Advanced refund-risk prediction
Online learning
SHAP-based explainability
Real-time anomaly monitoring
Multi-merchant risk intelligence
Automated risk-policy optimization
⚠️ Prototype Limitations

PayShield is a hackathon prototype and not a production payment-processing system.

Current limitations include:

Payment processing is simulated.
Bank authorization is simulated.
Risk scoring currently uses a weighted risk engine.
Merchant-loss calculations are prototype estimates.
Evaluation uses synthetic data.
Continuous learning is implemented as a feedback architecture rather than autonomous production model retraining.
Production deployment would require additional security, compliance, scalability, monitoring, and payment-provider integrations.
🏆 Razorpay AI Buildathon 2026
Track 02 — AI Risk Manager

Objective:

Stop the merchant losing money to fraud, returns and chargebacks.

PayShield AI addresses this objective by combining:

Fraud Detection + Payment Integrity + Behavioural Risk + Chargeback Risk + Refund Risk + Abuse Detection + Expected Loss + Recovery + Continuous Feedback

into a unified merchant risk-management platform.

💭 Design Philosophy

PayShield is built around one simple idea:

A payment should not only be evaluated for whether it can succeed — it should be evaluated for the risk and financial impact it can create for the merchant.

The system therefore follows:

DETECT
   ↓
ASSESS
   ↓
DECIDE
   ↓
ACT
   ↓
OBSERVE
   ↓
RECOVER
   ↓
LEARN

This creates a complete risk-management feedback loop.

📌 Final Takeaway

PayShield AI transforms a simulated payment gateway into an intelligent merchant loss-prevention system.

It combines:

Transaction-level risk scoring
Behavioural intelligence
Payment-integrity verification
Fraud-spike detection
Chargeback-risk analysis
Refund/return-risk analysis
Abuse-ring detection
Duplicate-payment detection
Expected merchant loss estimation
Explainable decisions
Agentic responses
Recovery workflows
Continuous feedback
Merchant analytics

The goal is not simply to stop fraud.

The goal is to:

Protect every payment. Prevent every avoidable loss.
Built for the Razorpay AI Buildathon 2026

PayShield AI — Intelligent Merchant Loss Prevention & Payment Risk Management