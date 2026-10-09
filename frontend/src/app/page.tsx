"use client";

import { useEffect, useMemo, useState } from "react";
import {
  CopilotChat,
  useAgent,
  useAgentContext,
} from "@copilotkit/react-core/v2";
import sampleFinancialData from "@/lib/sample-financial-data";

type Priority = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | string;

type Recommendation = {
  recommendation_id: string;
  priority: Priority;
  action: string;
  rationale: string;
  evidence_ids?: string[];
  advisor_only?: boolean;
};

type Anomaly = {
  anomaly_id: string;
  type: string;
  severity: Priority;
  description: string;
};

type AnalysisMetrics = {
  latest_month: string;
  monthly_income: number;
  monthly_expenses: number;
  net_cash_flow: number;
  savings_rate: number;
  expense_trend_pct: number;
  debt_to_income_pct: number;
  cash_buffer_months: number;
  portfolio_value: number;
  top_holding_concentration_pct: number;
};

type FinalResult = {
  client_id: string;
  run_id: string;
  data_quality?: {
    status: string;
    warnings?: string[];
    missing_sources?: string[];
    fallback_used?: boolean;
  };
  analysis: {
    metrics: AnalysisMetrics;
    anomalies: Anomaly[];
    risk_signals: string[];
    risk_level: string;
    trend: string;
    data_quality?: {
      status: string;
      warnings?: string[];
    };
  };
  analyzer_narrative?: {
    executive_summary?: string;
    risk_rationale?: string;
    priority_focus?: string[];
  };
  advisory: {
    summary: string;
    recommendations: Recommendation[];
    confidence?: number;
    disclaimer?: string;
  };
  review?: {
    status: string;
    reviewer_comment?: string;
    reviewed_at?: string;
  };
  memory_written?: boolean;
};

type ReviewRequest = {
  run_id: string;
  client_id: string;
  risk_level: string;
  summary: string;
  recommendations: Recommendation[];
  prompt: string;
};

type RunPayload = {
  run_id?: string;
  status: string;
  result?: FinalResult | null;
  review_request?: ReviewRequest | null;
  error?: string;
  details?: string;
  client_id?: string;
};

type Profile = {
  client_id?: string;
  as_of_date?: string;
  risk_profile?: string;
  annual_income?: number;
  cash_balance?: number;
  monthly_history?: Array<{
    month: string;
    income: number;
    expenses: number;
    savings?: number;
    investments?: number;
    debt_balance?: number;
  }>;
  transactions?: Array<{ currency?: string }>;
  holdings?: Array<{
    symbol: string;
    market_value: number;
    asset_class?: string;
  }>;
  goals?: Array<{
    name: string;
    target_amount: number;
    target_date?: string;
    priority?: string;
  }>;
};

function unwrapProfile(value: unknown): Profile | null {
  if (!value || typeof value !== "object") return null;

  const input = value as Record<string, unknown>;
  if (input.invalid_json) return null;

  const data = (input.financial_data ?? input) as Record<string, unknown>;

  if (!Array.isArray(data.monthly_history)) return null;

  return data as unknown as Profile;
}

function money(value: number | undefined, currency: string): string {
  if (value === undefined || !Number.isFinite(value)) return "—";

  try {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: /^[A-Z]{3}$/.test(currency) ? currency : "INR",
      maximumFractionDigits: 0,
    }).format(value);
  } catch {
    return `${currency} ${Math.round(value).toLocaleString("en-IN")}`;
  }
}

function percent(value: number | undefined): string {
  return value === undefined || !Number.isFinite(value)
    ? "—"
    : `${value.toFixed(1)}%`;
}

function numberLabel(value: number | undefined, suffix = ""): string {
  return value === undefined || !Number.isFinite(value)
    ? "—"
    : `${value.toFixed(1)}${suffix}`;
}

function profileCurrency(profile: Profile | null): string {
  const codes = [
    ...new Set(
      (profile?.transactions ?? [])
        .map((item) => (item.currency ?? "").toUpperCase())
        .filter(Boolean)
    ),
  ];

  if (codes.length === 1) return codes[0];
  if (codes.length > 1) return "MIXED";
  return "INR";
}

function derivePreview(profile: Profile | null) {
  if (!profile) return null;

  const months = [...(profile.monthly_history ?? [])].sort((a, b) =>
    a.month.localeCompare(b.month)
  );

  const latest = months[months.length - 1];

  const totalPortfolio = (profile.holdings ?? []).reduce(
    (sum, holding) => sum + (Number(holding.market_value) || 0),
    0
  );

  const topHolding = Math.max(
    0,
    ...(profile.holdings ?? []).map(
      (holding) => Number(holding.market_value) || 0
    )
  );

  return {
    latest,
    portfolioValue: totalPortfolio,
    cashBufferMonths:
      latest && latest.expenses > 0
        ? (Number(profile.cash_balance) || 0) / latest.expenses
        : undefined,
    concentrationPct:
      totalPortfolio > 0 ? (topHolding / totalPortfolio) * 100 : 0,
  };
}

function MetricCard({
  label,
  value,
  sub,
  icon,
  tone = "normal",
}: {
  label: string;
  value: string;
  sub: string;
  icon: string;
  tone?: string;
}) {
  return (
    <article className={`metric-card metric-${tone}`}>
      <div className="metric-top">
        <span>{label}</span>
        <span className="metric-icon">{icon}</span>
      </div>
      <strong>{value}</strong>
      <small>{sub}</small>
    </article>
  );
}

function PriorityTag({ priority }: { priority: string }) {
  return (
    <span className={`priority-tag priority-${priority.toLowerCase()}`}>
      {priority}
    </span>
  );
}

export default function HomePage() {
  const [profileText, setProfileText] = useState(
    JSON.stringify(sampleFinancialData, null, 2)
  );
  const [profileError, setProfileError] = useState("");
  const [payload, setPayload] = useState<RunPayload | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [reviewing, setReviewing] = useState(false);
  const [actionError, setActionError] = useState("");
  const [showProfile, setShowProfile] = useState(true);

  // The installed hook returns the agent; do not destructure isReady.
  const { agent } = useAgent({ agentId: "wealthAdvisor" });

  const parsed = useMemo(() => {
    try {
      return { value: JSON.parse(profileText), error: "" };
    } catch (error) {
      return {
        value: { invalid_json: true },
        error: error instanceof Error ? error.message : "Invalid JSON",
      };
    }
  }, [profileText]);

  const profile = useMemo(() => unwrapProfile(parsed.value), [parsed.value]);

  const remoteStatePayload = (
    agent.state as Record<string, unknown> | undefined
  )?.wealth_advisor as RunPayload | undefined;

  useEffect(() => {
    if (remoteStatePayload) setPayload(remoteStatePayload);
  }, [remoteStatePayload]);

  useAgentContext({
    description:
      "CURRENT_FINANCIAL_DATA_JSON: the current client profile from the editable JSON panel. Use this as user-provided data; do not claim it has been analyzed until a tool result confirms that.",
    value: parsed.error
      ? { invalid_json: true, error: parsed.error }
      : parsed.value,
  });

  useAgentContext({
    description:
      "CURRENT_WEALTH_ADVISOR_DASHBOARD_STATE: latest dashboard result. Preserve source currencies and distinguish pending review from completed analysis.",
    value: payload ?? { status: "not_analyzed" },
  });

  const result = payload?.result ?? null;
  const reviewRequest = payload?.review_request ?? null;
  const metrics = result?.analysis?.metrics;
  const preview = useMemo(() => derivePreview(profile), [profile]);
  const currency = profileCurrency(profile);
  const latest = preview?.latest;

  const displayIncome = metrics?.monthly_income ?? latest?.income;
  const displayExpenses = metrics?.monthly_expenses ?? latest?.expenses;
  const displayNetFlow =
    metrics?.net_cash_flow ??
    (latest ? latest.income - latest.expenses : undefined);
  const displayCashBuffer =
    metrics?.cash_buffer_months ?? preview?.cashBufferMonths;
  const displayPortfolio =
    metrics?.portfolio_value ?? preview?.portfolioValue;
  const displayConcentration =
    metrics?.top_holding_concentration_pct ?? preview?.concentrationPct;

  const recommendations =
    result?.advisory?.recommendations ??
    reviewRequest?.recommendations ??
    [];

  const riskLevel =
    result?.analysis?.risk_level ?? reviewRequest?.risk_level ?? "—";

  const trend = result?.analysis?.trend ?? "Awaiting analysis";
  const dataQuality =
    result?.data_quality?.status ??
    (payload?.status === "pending_review"
      ? "analysis reached review"
      : "not analyzed");

  const summary =
    result?.analyzer_narrative?.executive_summary ??
    result?.advisory?.summary ??
    reviewRequest?.summary ??
    payload?.error ??
    "Your deterministic analysis and advisor recommendations will appear here.";

  const warnings =
    result?.data_quality?.warnings ??
    result?.analysis?.data_quality?.warnings ??
    [];

  const currencySet = [
    ...new Set(
      (profile?.transactions ?? [])
        .map((item) => (item.currency ?? "").toUpperCase())
        .filter(Boolean)
    ),
  ];

  const currencyWarning = currencySet.length > 1;

  async function runAnalysis() {
    setActionError("");
    setProfileError("");

    if (parsed.error) {
      setProfileError(`Invalid JSON: ${parsed.error}`);
      return;
    }

    const currentProfile =
      parsed.value?.financial_data ?? parsed.value;

    setAnalyzing(true);

    try {
      const response = await fetch("/api/wealth/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ financial_data: currentProfile }),
      });

      const data = (await response.json()) as RunPayload & {
        detail?: string;
      };

      if (!response.ok) {
        throw new Error(
          data.detail ??
            data.error ??
            `Analysis failed with HTTP ${response.status}`
        );
      }

      setPayload(data);
    } catch (error) {
      setActionError(
        error instanceof Error ? error.message : "Could not run analysis."
      );
    } finally {
      setAnalyzing(false);
    }
  }

  async function submitReview(decision: "APPROVE" | "REJECT") {
    const runId = payload?.run_id ?? reviewRequest?.run_id;
    if (!runId) return;

    setReviewing(true);
    setActionError("");

    try {
      const response = await fetch(
        `/api/wealth/runs/${encodeURIComponent(runId)}/review`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ decision }),
        }
      );

      const data = (await response.json()) as RunPayload & {
        detail?: string;
      };

      if (!response.ok) {
        throw new Error(
          data.detail ?? `Review failed with HTTP ${response.status}`
        );
      }

      setPayload(data);
    } catch (error) {
      setActionError(
        error instanceof Error ? error.message : "Could not submit review."
      );
    } finally {
      setReviewing(false);
    }
  }

  function loadSample() {
    setProfileText(JSON.stringify(sampleFinancialData, null, 2));
    setProfileError("");
    setActionError("");
  }

  function importJsonFile(file?: File) {
    if (!file) return;

    if (!file.name.toLowerCase().endsWith(".json")) {
      setProfileError(
        "Choose a .json file containing a financial_data object or client profile."
      );
      return;
    }

    const reader = new FileReader();

    reader.onload = () => {
      setProfileText(String(reader.result ?? ""));
      setProfileError("");
    };

    reader.onerror = () => {
      setProfileError("Could not read that file.");
    };

    reader.readAsText(file);
  }

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <div className="brand-mark">
            W<span>·</span>
          </div>
          <div>
            <div className="brand-name">
              WEALTH<span> / </span>ADVISOR
            </div>
            <div className="brand-subtitle">Intelligence workspace</div>
          </div>
        </div>

        <div className="topbar-status">
          <span className={`status-dot ${agent.isRunning ? "online" : ""}`} />
          AG-UI agent selected
          <span className="topbar-divider" />
          {agent.isRunning ? "Working…" : "Ready"}
        </div>

        <div className="topbar-profile">
          <div className="avatar">
            {(profile?.client_id ?? "WA").slice(0, 2).toUpperCase()}
          </div>
          <div>
            <strong>{profile?.client_id ?? "No client loaded"}</strong>
            <small>Advisor workspace</small>
          </div>
        </div>
      </header>

      <div className="page-intro">
        <div>
          <p className="eyebrow">CLIENT INTELLIGENCE / LIVE WORKSPACE</p>
          <h1>
            Financial overview<span className="title-period">.</span>
          </h1>
          <p className="intro-copy">
            A grounded view of cash flow, portfolio signals, and the next best
            advisor conversation.
          </p>
        </div>

        <div className="intro-actions">
          <button
            className="button button-muted"
            onClick={() => setShowProfile((value) => !value)}
          >
            {showProfile ? "Hide profile JSON" : "Edit profile JSON"}
          </button>

          <button
            className="button button-primary"
            onClick={runAnalysis}
            disabled={analyzing || Boolean(parsed.error)}
          >
            {analyzing ? (
              <>
                <span className="spinner" /> Analyzing
              </>
            ) : (
              <>
                <span>✦</span> Analyze profile
              </>
            )}
          </button>
        </div>
      </div>

      {showProfile ? (
        <section className="profile-panel panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">INPUT PROFILE</p>
              <h2>Client data source</h2>
              <p>
                Paste validated JSON or import a file. The current profile is
                shared with the chat agent as context.
              </p>
            </div>

            <div className="profile-actions">
              <label className="button button-outline file-button">
                Import JSON
                <input
                  type="file"
                  accept="application/json,.json"
                  onChange={(event) =>
                    importJsonFile(event.target.files?.[0])
                  }
                />
              </label>

              <button
                className="button button-outline"
                onClick={loadSample}
              >
                Reset sample
              </button>
            </div>
          </div>

          <textarea
            className="json-editor"
            spellCheck={false}
            value={profileText}
            onChange={(event) => setProfileText(event.target.value)}
            aria-label="Client financial data JSON"
          />

          {parsed.error || profileError ? (
            <p className="inline-error">
              {profileError || `Invalid JSON: ${parsed.error}`}
            </p>
          ) : (
            <p className="helper-line">
              {profile?.client_id ?? "Unknown client"} ·{" "}
              {profile?.risk_profile ?? "Risk profile missing"} ·{" "}
              {profile?.transactions?.length ?? 0} transactions ·{" "}
              {profile?.holdings?.length ?? 0} holdings
            </p>
          )}
        </section>
      ) : null}

      <section className="metric-grid" aria-label="Key financial metrics">
        <MetricCard
          label="MONTHLY INCOME"
          value={money(displayIncome, currency)}
          sub={
            metrics?.latest_month
              ? `Verified · ${metrics.latest_month}`
              : `Profile snapshot · ${latest?.month ?? "—"}`
          }
          icon="↗"
          tone="green"
        />

        <MetricCard
          label="MONTHLY EXPENSES"
          value={money(displayExpenses, currency)}
          sub={
            metrics
              ? `Trend ${numberLabel(metrics.expense_trend_pct, "%")}`
              : "Awaiting deterministic analysis"
          }
          icon="↘"
          tone="amber"
        />

        <MetricCard
          label="NET CASH FLOW"
          value={money(displayNetFlow, currency)}
          sub={
            metrics
              ? `Savings rate ${percent(metrics.savings_rate)}`
              : "Income less latest expenses"
          }
          icon="⌁"
          tone={
            typeof displayNetFlow === "number" && displayNetFlow < 0
              ? "red"
              : "blue"
          }
        />

        <MetricCard
          label="CASH BUFFER"
          value={numberLabel(displayCashBuffer, " mo")}
          sub={
            metrics
              ? "Deterministic analysis"
              : "Cash balance ÷ latest expenses"
          }
          icon="◷"
          tone={
            typeof displayCashBuffer === "number" && displayCashBuffer < 3
              ? "amber"
              : "green"
          }
        />

        <MetricCard
          label="PORTFOLIO VALUE"
          value={money(displayPortfolio, currency)}
          sub={`${numberLabel(displayConcentration, "%")} top-holding concentration`}
          icon="◈"
          tone="violet"
        />
      </section>

      {!result && payload?.status === "pending_review" ? (
        <p className="snapshot-note">
          Metrics above are a profile snapshot while this run awaits review.
        </p>
      ) : null}

      {currencyWarning ? (
        <p className="inline-warning">
          This profile contains more than one transaction currency. Amounts use
          MIXED without conversion; do not compare currencies without explicit
          exchange rates.
        </p>
      ) : null}

      <section className="workspace-grid">
        <div className="dashboard-column">
          <section className="panel health-panel">
            <div className="panel-heading compact">
              <div>
                <p className="eyebrow">ANALYSIS BRIEF</p>
                <h2>Risk &amp; trajectory</h2>
              </div>
              <span
                className={`risk-badge risk-${String(riskLevel).toLowerCase()}`}
              >
                {riskLevel}
              </span>
            </div>

            <p className="analysis-summary">{summary}</p>

            <div className="brief-footer">
              <span className="trend-chip">
                <span className="chip-dot" /> {trend}
              </span>
              <span className="quality-text">
                Data quality: <strong>{dataQuality}</strong>
              </span>
              {payload?.run_id ? (
                <span className="run-id">Run {payload.run_id}</span>
              ) : null}
            </div>
          </section>

          {payload?.status === "pending_review" && reviewRequest ? (
            <section className="panel review-panel">
              <div className="review-banner">
                <div className="review-icon">!</div>
                <div>
                  <p className="eyebrow">HUMAN-IN-THE-LOOP</p>
                  <h2>Advisor review required</h2>
                  <p>Review this decision support before client-facing action.</p>
                </div>
                <PriorityTag priority={reviewRequest.risk_level} />
              </div>

              <p className="review-prompt">{reviewRequest.prompt}</p>

              <div className="review-actions">
                <button
                  className="button button-outline"
                  disabled={reviewing}
                  onClick={() => submitReview("REJECT")}
                >
                  Reject recommendations
                </button>
                <button
                  className="button button-primary"
                  disabled={reviewing}
                  onClick={() => submitReview("APPROVE")}
                >
                  {reviewing ? "Submitting…" : "Approve review"}
                </button>
              </div>

              <p className="security-note">
                Approval records the human decision. It does not execute trades
                or move money.
              </p>
            </section>
          ) : null}

          {result?.review ? (
            <section className="panel review-outcome">
              <div className="panel-heading compact">
                <div>
                  <p className="eyebrow">REVIEW RECORD</p>
                  <h2>Review outcome</h2>
                </div>
                <span
                  className={`review-status status-${result.review.status}`}
                >
                  {result.review.status.replaceAll("_", " ")}
                </span>
              </div>
              <p>
                {result.review.reviewer_comment ??
                  "This run has reached its review outcome."}
              </p>
              {result.review.reviewed_at ? (
                <small>
                  Recorded at{" "}
                  {new Date(result.review.reviewed_at).toLocaleString()}
                </small>
              ) : null}
            </section>
          ) : null}

          <section className="panel chart-panel">
            <div className="panel-heading compact">
              <div>
                <p className="eyebrow">CASH FLOW</p>
                <h2>Income vs. spending</h2>
              </div>
              <span className="panel-unit">{currency}</span>
            </div>

            <div className="chart-legend">
              <span><i className="legend-income" />Income</span>
              <span><i className="legend-expense" />Expenses</span>
            </div>

            <div className="bars-chart">
              {(profile?.monthly_history ?? [])
                .slice()
                .sort((a, b) => a.month.localeCompare(b.month))
                .map((month) => {
                  const max = Math.max(
                    1,
                    ...(profile?.monthly_history ?? []).flatMap((entry) => [
                      entry.income,
                      entry.expenses,
                    ])
                  );

                  return (
                    <div className="chart-month" key={month.month}>
                      <div className="bar-pair">
                        <div
                          className="chart-bar income-bar"
                          title={`Income ${money(month.income, currency)}`}
                          style={{
                            height: `${Math.max(
                              2,
                              (month.income / max) * 100
                            )}%`,
                          }}
                        />
                        <div
                          className="chart-bar expense-bar"
                          title={`Expenses ${money(month.expenses, currency)}`}
                          style={{
                            height: `${Math.max(
                              2,
                              (month.expenses / max) * 100
                            )}%`,
                          }}
                        />
                      </div>
                      <span>{month.month.slice(5)}</span>
                    </div>
                  );
                })}

              {!profile?.monthly_history?.length ? (
                <p className="empty-state">
                  Add monthly history to see cash flow.
                </p>
              ) : null}
            </div>

            <p className="chart-caption">
              Profile history, sorted by month. The analysis engine separately
              evaluates trends and anomalies.
            </p>
          </section>

          <section className="panel anomalies-panel">
            <div className="panel-heading compact">
              <div>
                <p className="eyebrow">SIGNAL DETECTION</p>
                <h2>Insights &amp; anomalies</h2>
              </div>
              <span className="count-pill">
                {result?.analysis?.anomalies?.length ?? "—"} signals
              </span>
            </div>

            {result?.analysis?.anomalies?.length ? (
              <div className="signal-list">
                {result.analysis.anomalies.map((anomaly) => (
                  <article className="signal-row" key={anomaly.anomaly_id}>
                    <div
                      className={`signal-marker severity-${anomaly.severity.toLowerCase()}`}
                    />
                    <div className="signal-copy">
                      <div className="signal-heading">
                        <strong>{anomaly.type.replaceAll("_", " ")}</strong>
                        <PriorityTag priority={anomaly.severity} />
                      </div>
                      <p>{anomaly.description}</p>
                      <small>{anomaly.anomaly_id}</small>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="empty-state padded">
                {payload
                  ? "No completed anomaly set is available for this run yet."
                  : "Run an analysis to surface spending, liquidity, debt, and concentration signals."}
              </div>
            )}

            {warnings.length ? (
              <div className="warning-list">
                {warnings.map((warning, index) => (
                  <p key={`${warning}-${index}`}>• {warning}</p>
                ))}
              </div>
            ) : null}
          </section>

          <section className="panel recommendations-panel">
            <div className="panel-heading compact">
              <div>
                <p className="eyebrow">ADVISOR WORKLIST</p>
                <h2>Recommended discussion points</h2>
              </div>
              <span className="count-pill">{recommendations.length} items</span>
            </div>

            {recommendations.length ? (
              <div className="recommendation-list">
                {recommendations.map((recommendation, index) => (
                  <article
                    className="recommendation-card"
                    key={recommendation.recommendation_id || index}
                  >
                    <div className="rec-index">
                      {String(index + 1).padStart(2, "0")}
                    </div>
                    <div className="rec-body">
                      <div className="rec-heading">
                        <PriorityTag priority={recommendation.priority} />
                        <span className="rec-id">
                          {recommendation.recommendation_id}
                        </span>
                      </div>
                      <h3>{recommendation.action}</h3>
                      <p>{recommendation.rationale}</p>

                      {recommendation.evidence_ids?.length ? (
                        <div className="evidence-tags">
                          {recommendation.evidence_ids.map((id) => (
                            <span key={id}>{id}</span>
                          ))}
                        </div>
                      ) : null}

                      {recommendation.advisor_only ? (
                        <small className="advisor-only">
                          Advisor-only follow-up
                        </small>
                      ) : null}
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <div className="empty-state padded">
                Once the workflow has generated decision support, evidence-linked
                recommendations will appear here.
              </div>
            )}

            {result?.advisory?.disclaimer ? (
              <p className="disclaimer">{result.advisory.disclaimer}</p>
            ) : null}
          </section>

          <section className="panel goals-panel">
            <div className="panel-heading compact">
              <div>
                <p className="eyebrow">GOAL TRACKER</p>
                <h2>Client objectives</h2>
              </div>
              <span className="count-pill">
                {profile?.goals?.length ?? 0} goals
              </span>
            </div>

            {profile?.goals?.length ? (
              <div className="goal-list">
                {profile.goals.map((goal, index) => (
                  <div
                    className="goal-row"
                    key={`${goal.name}-${index}`}
                  >
                    <div className="goal-symbol">◎</div>
                    <div className="goal-description">
                      <strong>{goal.name}</strong>
                      <small>
                        {goal.target_date
                          ? `Target ${goal.target_date}`
                          : "Target date not set"}
                      </small>
                    </div>
                    <div className="goal-value">
                      <strong>{money(goal.target_amount, currency)}</strong>
                      <PriorityTag priority={goal.priority ?? "MEDIUM"} />
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="empty-state padded">
                Add goals to the input profile to include them here.
              </div>
            )}
          </section>
        </div>

        <aside className="copilot-column">
          <div className="copilot-heading">
            <div>
              <p className="eyebrow">ADAPTIVE AGENT WORKSPACE</p>
              <h2>Ask Wealth Advisor</h2>
              <p>
                The assistant can change the response layout to fit your
                question—not just return paragraphs.
              </p>
            </div>
            <span className="copilot-spark">✦</span>
          </div>

          <div className="prompt-hints">
            <span>Ask for any useful view</span>
            <p>“Summarize my financial health as KPI cards.”</p>
            <p>“Compare income and expenses across months in a chart.”</p>
            <p>“Show my goals as a progress view and timeline.”</p>
            <p>“Put the top risks and evidence in a table.”</p>
            <small>
              Visual answers require the backend and frontend A2UI integrations
              to be configured correctly.
            </small>
          </div>

          <div className="copilot-chat-wrap">
            <CopilotChat agentId="wealthAdvisor" />
          </div>

          <div className="agent-capabilities">
            <div>
              <span className="capability-icon">↗</span>
              <p>
                <strong>Grounded analysis</strong>
                <small>
                  Financial calculations come from the backend analysis engine.
                </small>
              </p>
            </div>
            <div>
              <span className="capability-icon">▦</span>
              <p>
                <strong>Adaptive response UI</strong>
                <small>
                  A2UI can compose cards, charts, tables, progress views, and
                  timelines when the agent emits supported UI output.
                </small>
              </p>
            </div>
            <div>
              <span className="capability-icon">✓</span>
              <p>
                <strong>Human review</strong>
                <small>
                  Risk-gated recommendations remain under advisor control.
                </small>
              </p>
            </div>
          </div>
        </aside>
      </section>

      {actionError ? (
        <div role="alert" className="toast-error">
          {actionError}
          <button
            onClick={() => setActionError("")}
            aria-label="Dismiss error"
          >
            ×
          </button>
        </div>
      ) : null}

      <footer className="page-footer">
        <span>
          WEALTH ADVISOR ASSISTANT <span className="footer-dot">·</span>{" "}
          DEVELOPMENT WORKSPACE
        </span>
        <span>Decision support only · Verify data before client action</span>
      </footer>
    </main>
  );
}