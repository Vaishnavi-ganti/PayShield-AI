/* =========================================================
   PAYSHIELD AI — FRONTEND CONTROLLER
========================================================= */

let latestRiskData = null;
let latestPaymentId = null;


/* =========================================================
   HELPERS
========================================================= */

function $(id) {
    return document.getElementById(id);
}


function money(value) {

    const number = Number(value || 0);

    return "₹" + number.toLocaleString("en-IN", {
        maximumFractionDigits: 0
    });
}


function number(value) {

    return Number(value || 0).toLocaleString("en-IN");
}


function percentage(value) {

    return Number(value || 0).toFixed(1) + "%";
}


function safe(value) {

    if (value === null || value === undefined) {
        return "—";
    }

    return value;
}


async function postJSON(url, body) {

    const response = await fetch(url, {

        method: "POST",

        headers: {
            "Content-Type": "application/json"
        },

        body: JSON.stringify(body)

    });

    const data = await response.json();

    if (!response.ok) {

        throw new Error(
            data.error ||
            "Request failed"
        );

    }

    return data;
}


/* =========================================================
   INPUT
========================================================= */

function getTransactionInput() {

    return {

        customer:
            $("customer").value.trim() ||
            "Vaishnavi",

        amount:
            Number($("amount").value || 0),

        device_id:
            $("deviceId").value.trim() ||
            "DEVICE_001",

        order_id:
            $("orderId").value.trim() ||
            "ORDER_001"

    };
}


/* =========================================================
   ANALYZE RISK
========================================================= */

async function analyzeRisk() {

    const input = getTransactionInput();

    if (input.amount <= 0) {

        alert("Enter a valid payment amount.");

        return;
    }


    setLoading(true);

    try {

        const data = await postJSON(
            "/internal-risk-analysis",
            input
        );

        latestRiskData = data;

        renderRiskResult(data);

        renderAgent(data);

        renderSignals(data);

    } catch (error) {

        console.error(error);

        alert(
            "Risk analysis failed: " +
            error.message
        );

    } finally {

        setLoading(false);

    }
}


/* =========================================================
   PROCESS PAYMENT
========================================================= */

async function processPayment() {

    const input = getTransactionInput();

    if (input.amount <= 0) {

        alert("Enter a valid payment amount.");

        return;
    }


    setLoading(true);

    try {

        const data = await postJSON(
            "/create-payment",
            input
        );

        latestRiskData = data;

        latestPaymentId =
            data.payment_id ||
            data.id ||
            latestPaymentId;


        renderRiskResult(data);

        renderAgent(data);

        renderSignals(data);

        await loadDashboard();

        showToast(
            "Payment processed: " +
            safe(data.status)
        );

    } catch (error) {

        console.error(error);

        alert(
            "Payment processing failed: " +
            error.message
        );

    } finally {

        setLoading(false);

    }
}


/* =========================================================
   PAYMENT MISMATCH
========================================================= */

async function simulateMismatch() {

    const input = getTransactionInput();

    try {

        setLoading(true);

        const data = await postJSON(
            "/create-payment",
            {
                ...input,
                simulate_integrity: "MISMATCH"
            }
        );

        latestRiskData = data;

        latestPaymentId =
            data.payment_id ||
            data.id ||
            latestPaymentId;


        renderRiskResult(data);

        renderAgent(data);

        renderSignals(data);

        await loadDashboard();

        showToast(
            "Payment integrity mismatch simulated"
        );

    } catch (error) {

        console.error(error);

        alert(
            "Mismatch simulation failed: " +
            error.message
        );

    } finally {

        setLoading(false);

    }
}


/* =========================================================
   RENDER RISK RESULT
========================================================= */

function renderRiskResult(data) {

    $("riskResult").style.display = "block";


    const score =
        Number(
            data.risk_score ??
            data.score ??
            0
        );


    const decision =
        String(
            data.decision ||
            "UNKNOWN"
        ).toUpperCase();


    const level =
        data.risk_level ||
        data.riskLevel ||
        "—";


    const loss =
        data.expected_loss ??
        data.expectedLoss ??
        0;


    const action =
        data.agent_action ||
        data.agentAction ||
        decision;


    $("resultScore").textContent =
        score.toFixed(1);


    $("resultLoss").textContent =
        money(loss);


    $("resultLevel").textContent =
        safe(level);


    $("resultAction").textContent =
        safe(action);


    const badge =
        $("decisionBadge");


    badge.textContent =
        decision;


    badge.className =
        "decision-badge " +
        decision;


    renderReasons(
        data.explanation ||
        data.reasons ||
        []
    );

}


/* =========================================================
   REASONS / EXPLAINABLE AI
========================================================= */

function renderReasons(reasons) {

    const list =
        $("riskReasons");

    list.innerHTML = "";


    if (typeof reasons === "string") {

        reasons = [reasons];

    }


    if (!Array.isArray(reasons) ||
        reasons.length === 0) {

        const li =
            document.createElement("li");

        li.textContent =
            "No additional risk explanation returned.";

        list.appendChild(li);

        return;
    }


    reasons.forEach(reason => {

        const li =
            document.createElement("li");

        li.textContent =
            typeof reason === "object"
                ? (
                    reason.reason ||
                    reason.message ||
                    JSON.stringify(reason)
                )
                : String(reason);

        list.appendChild(li);

    });

}


/* =========================================================
   AGENT
========================================================= */

function renderAgent(data) {

    const score =
        Number(
            data.risk_score ??
            data.score ??
            0
        );


    const level =
        data.risk_level ||
        "—";


    const loss =
        data.expected_loss ??
        0;


    const action =
        data.agent_action ||
        data.decision ||
        "—";


    const decision =
        data.decision ||
        "WAITING";


    $("agentRiskScore").textContent =
        score.toFixed(1);


    $("agentRiskLevel").textContent =
        String(level).toUpperCase();


    $("agentExpectedLoss").textContent =
        money(loss);


    $("agentAction").textContent =
        String(action).toUpperCase();


    $("agentRecommendation").textContent =
        buildAgentRecommendation(
            decision,
            action,
            score
        );

}


/* =========================================================
   AGENT EXPLANATION
========================================================= */

function buildAgentRecommendation(
    decision,
    action,
    score
) {

    const d =
        String(decision).toUpperCase();

    const a =
        String(action || "").toUpperCase();


    if (d === "BLOCK") {

        return (
            "BLOCK — risk is high enough that " +
            "preventing merchant exposure is preferred."
        );

    }


    if (d === "REVIEW") {

        return (
            "REVIEW — elevated risk detected; " +
            "merchant review is recommended."
        );

    }


    if (d === "VERIFY") {

        return (
            "VERIFY — moderate risk detected; " +
            "additional verification preserves customer access."
        );

    }


    if (d === "ALLOW") {

        return (
            "ALLOW — transaction risk is low; " +
            "avoid unnecessary customer friction."
        );

    }


    if (a) {

        return (
            "Agent action: " +
            a
        );

    }


    return (
        "Waiting for transaction investigation..."
    );

}


/* =========================================================
   RISK SIGNALS
========================================================= */

function renderSignals(data) {

    const components =
        data.components ||
        data.risk_components ||
        {};


    setSignal(
        "behaviour",
        findComponent(
            components,
            [
                "behaviour",
                "behavior",
                "behavioural",
                "behavioral",
                "behavioural_anomaly"
            ]
        )
    );


    setSignal(
        "velocity",
        findComponent(
            components,
            [
                "velocity",
                "velocity_attack"
            ]
        )
    );


    setSignal(
        "fraud",
        findComponent(
            components,
            [
                "fraud_spike",
                "fraud",
                "fraud_spike_detection"
            ]
        )
    );


    setSignal(
        "chargeback",
        findComponent(
            components,
            [
                "chargeback",
                "chargeback_risk"
            ]
        )
    );


    setSignal(
        "refund",
        findComponent(
            components,
            [
                "refund",
                "return",
                "refund_return",
                "return_refund"
            ]
        )
    );


    setSignal(
        "abuse",
        findComponent(
            components,
            [
                "abuse_ring",
                "abuse",
                "ring"
            ]
        )
    );


    setSignal(
        "integrity",
        findComponent(
            components,
            [
                "payment_integrity",
                "integrity"
            ]
        )
    );


    setSignal(
        "duplicate",
        findComponent(
            components,
            [
                "duplicate",
                "duplicate_payment"
            ]
        )
    );

}


function findComponent(
    components,
    names
) {

    for (const name of names) {

        if (
            components &&
            components[name] !== undefined
        ) {

            return components[name];

        }

    }


    return 0;
}


function setSignal(
    name,
    value
) {

    const score =
        normalizeScore(value);


    const bar =
        $(name + "Bar");


    const label =
        $(name + "Score");


    if (!bar || !label) {
        return;
    }


    bar.style.width =
        Math.max(
            0,
            Math.min(100, score)
        ) + "%";


    label.textContent =
        score.toFixed(0);

}


/* =========================================================
   SCORE NORMALIZATION
========================================================= */

function normalizeScore(value) {

    if (
        typeof value === "object" &&
        value !== null
    ) {

        value =
            value.score ??
            value.risk ??
            value.value ??
            0;

    }


    const score =
        Number(value || 0);


    if (score <= 1 && score > 0) {

        return score * 100;

    }


    return Math.max(
        0,
        Math.min(100, score)
    );

}


/* =========================================================
   DASHBOARD
========================================================= */

async function loadDashboard() {

    try {

        const response =
            await fetch(
                "/api/risk-dashboard"
            );


        const data =
            await response.json();


        renderDashboard(data);

    } catch (error) {

        console.error(
            "Dashboard error:",
            error
        );

    }

}


function renderDashboard(data) {

    const summary =
        data.summary ||
        data;


    $("totalTransactions").textContent =
        number(
            summary.total_transactions
        );


    $("blockedTransactions").textContent =
        number(
            summary.blocked
        );


    $("expectedLoss").textContent =
        money(
            summary.expected_loss
        );


    $("lossPrevented").textContent =
        money(
            summary.estimated_loss_prevented
        );


    $("totalValue").textContent =
        money(
            summary.total_value
        );


    $("successfulCount").textContent =
        number(
            summary.successful
        );


    $("verificationCount").textContent =
        number(
            summary.verification
        );


    $("failedCount").textContent =
        number(
            summary.failed
        );


    const total =
        Number(
            summary.total_transactions || 0
        );


    const blocked =
        Number(
            summary.blocked || 0
        );


    const rate =
        total > 0
            ? (blocked / total) * 100
            : 0;


    $("protectionRate").textContent =
        percentage(rate);


    renderTransactionTable(
        data.recent_transactions ||
        []
    );

}


/* =========================================================
   TRANSACTION TABLE
========================================================= */

function renderTransactionTable(
    transactions
) {

    const tbody =
        $("transactionTable");


    if (
        !Array.isArray(transactions) ||
        transactions.length === 0
    ) {

        tbody.innerHTML = `
            <tr>
                <td colspan="7"
                    class="empty-state">
                    Waiting for transaction activity...
                </td>
            </tr>
        `;

        return;

    }


    tbody.innerHTML =
        transactions
            .slice(0, 15)
            .map(transaction => {

                const payment =
                    transaction.payment_id ||
                    transaction.id ||
                    "—";


                const customer =
                    transaction.customer ||
                    transaction.customer_name ||
                    "—";


                const amount =
                    transaction.amount ||
                    0;


                const risk =
                    transaction.risk_score ??
                    transaction.score ??
                    "—";


                const decision =
                    String(
                        transaction.decision ||
                        "—"
                    ).toUpperCase();


                const status =
                    String(
                        transaction.status ||
                        "—"
                    ).toUpperCase();


                const time =
                    formatTime(
                        transaction.created_at ||
                        transaction.timestamp
                    );


                return `
                    <tr>

                        <td>
                            ${escapeHTML(payment)}
                        </td>

                        <td>
                            ${escapeHTML(customer)}
                        </td>

                        <td>
                            ${money(amount)}
                        </td>

                        <td class="table-risk">
                            ${safe(risk)}
                        </td>

                        <td>
                            <span
                                class="table-decision ${decision}">
                                ${escapeHTML(decision)}
                            </span>
                        </td>

                        <td>
                            <span
                                class="table-status ${status}">
                                ${escapeHTML(status)}
                            </span>
                        </td>

                        <td>
                            ${escapeHTML(time)}
                        </td>

                    </tr>
                `;

            })
            .join("");

}


/* =========================================================
   RECOVERY AGENT
========================================================= */

async function reportOutcome(
    outcome
) {

    if (!latestPaymentId) {

        alert(
            "Process a payment first so the outcome can be attached to it."
        );

        return;
    }


    try {

        const data =
            await postJSON(
                "/report-outcome",
                {
                    payment_id:
                        latestPaymentId,

                    outcome:
                        outcome
                }
            );


        const message =
            data.recovery_action ||
            data.message ||
            (
                "Outcome recorded: " +
                outcome
            );


        $("recoveryMessage").textContent =
            message;


        await loadDashboard();


        showToast(
            "Outcome recorded: " +
            outcome
        );


    } catch (error) {

        console.error(error);

        alert(
            "Recovery action failed: " +
            error.message
        );

    }

}


/* =========================================================
   ASK AGENT
========================================================= */

function toggleAgentChat() {

    const chat =
        $("agentChat");


    chat.style.display =
        chat.style.display === "block"
            ? "none"
            : "block";

}


function askAgent(type) {

    const answer =
        $("chatAnswer");


    if (!latestRiskData) {

        answer.textContent =
            "Analyze a transaction first. The agent needs a current risk investigation before it can explain the decision.";

        return;
    }


    const data =
        latestRiskData;


    const score =
        Number(
            data.risk_score ??
            data.score ??
            0
        );


    const decision =
        String(
            data.decision ||
            "UNKNOWN"
        ).toUpperCase();


    const loss =
        money(
            data.expected_loss ||
            0
        );


    const reasons =
        data.explanation ||
        data.reasons ||
        [];


    switch (type) {

        case "decision":

            answer.textContent =
                `The agent selected ${decision} because the transaction risk score is ${score.toFixed(1)}/100. PayShield applies different actions according to the level of risk rather than blocking every suspicious payment.`;

            break;


        case "signals":

            if (
                Array.isArray(reasons) &&
                reasons.length
            ) {

                answer.textContent =
                    reasons.join(" ");

            } else {

                answer.textContent =
                    "The decision is based on multiple risk signals including behavioural anomalies, velocity, fraud-spike activity, chargeback risk, refund risk, abuse-ring indicators, payment integrity and duplicate-payment checks.";

            }

            break;


        case "loss":

            answer.textContent =
                `The estimated merchant exposure for this transaction is ${loss}. PayShield considers transaction risk together with configurable merchant-loss assumptions.`;

            break;


        case "action":

            answer.textContent =
                `The agent chose ${decision} to balance merchant protection against customer friction. Lower-risk payments can proceed, while higher-risk payments receive progressively stronger intervention.`;

            break;


        case "learning":

            answer.textContent =
                "After an outcome such as legitimate payment, refund or chargeback is observed, PayShield records feedback and uses the outcome as part of its risk-learning loop.";

            break;


        default:

            answer.textContent =
                "The agent is ready.";

    }

}


/* =========================================================
   RESET
========================================================= */

async function resetDemo() {

    const confirmed =
        confirm(
            "Reset the PayShield demo data?"
        );


    if (!confirmed) {
        return;
    }


    try {

        const response =
            await fetch(
                "/api/reset-demo",
                {
                    method: "POST"
                }
            );


        const data =
            await response.json();


        latestRiskData = null;
        latestPaymentId = null;


        $("riskResult").style.display =
            "none";


        $("agentRiskScore").textContent =
            "—";


        $("agentRiskLevel").textContent =
            "WAITING";


        $("agentExpectedLoss").textContent =
            "—";


        $("agentAction").textContent =
            "—";


        $("agentRecommendation").textContent =
            "Waiting for transaction investigation...";


        $("recoveryMessage").textContent =
            "No recovery event triggered.";


        await loadDashboard();


        showToast(
            data.message ||
            "Demo reset successfully"
        );


    } catch (error) {

        console.error(error);

        alert(
            "Reset failed: " +
            error.message
        );

    }

}


/* =========================================================
   LOADING STATE
========================================================= */

function setLoading(isLoading) {

    const buttons =
        document.querySelectorAll(
            ".primary-button, " +
            ".secondary-button, " +
            ".danger-button"
        );


    buttons.forEach(button => {

        button.disabled =
            isLoading;

        button.style.opacity =
            isLoading
                ? "0.55"
                : "1";

    });

}


/* =========================================================
   TOAST
========================================================= */

function showToast(message) {

    let toast =
        document.getElementById(
            "payShieldToast"
        );


    if (!toast) {

        toast =
            document.createElement(
                "div"
            );


        toast.id =
            "payShieldToast";


        toast.style.position =
            "fixed";

        toast.style.right =
            "22px";

        toast.style.bottom =
            "22px";

        toast.style.zIndex =
            "9999";

        toast.style.padding =
            "11px 15px";

        toast.style.border =
            "1px solid #2d4059";

        toast.style.borderRadius =
            "8px";

        toast.style.background =
            "#111c2b";

        toast.style.color =
            "#dce5f1";

        toast.style.fontSize =
            "10px";

        toast.style.boxShadow =
            "0 10px 30px rgba(0,0,0,.35)";


        document.body.appendChild(
            toast
        );

    }


    toast.textContent =
        message;


    toast.style.opacity =
        "1";


    clearTimeout(
        window.payShieldToastTimer
    );


    window.payShieldToastTimer =
        setTimeout(() => {

            toast.style.opacity =
                "0";

        }, 2600);

}


/* =========================================================
   UTILITIES
========================================================= */

function formatTime(value) {

    if (!value) {
        return "—";
    }


    try {

        const date =
            new Date(value);


        if (
            Number.isNaN(
                date.getTime()
            )
        ) {

            return String(value);

        }


        return date.toLocaleTimeString(
            "en-IN",
            {
                hour: "2-digit",
                minute: "2-digit"
            }
        );

    } catch {

        return String(value);

    }

}


function escapeHTML(value) {

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");

}


/* =========================================================
   NAV ACTIVE STATE
========================================================= */

document
    .querySelectorAll(".nav-item")
    .forEach(item => {

        item.addEventListener(
            "click",
            () => {

                document
                    .querySelectorAll(
                        ".nav-item"
                    )
                    .forEach(
                        nav =>
                            nav.classList.remove(
                                "active"
                            )
                    );


                item.classList.add(
                    "active"
                );

            }
        );

    });


/* =========================================================
   START DASHBOARD
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        loadDashboard();


        /*
         * Refresh operational dashboard
         * every five seconds.
         */
        setInterval(
            loadDashboard,
            5000
        );

    }
);