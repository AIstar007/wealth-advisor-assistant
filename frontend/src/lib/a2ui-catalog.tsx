"use client";

import type { ReactNode } from "react";
import {
  createCatalog,
  type CatalogDefinitions,
  type CatalogRenderers,
} from "@copilotkit/a2ui-renderer";
import { z } from "zod";

/**
 * Approved components the agent may compose into an A2UI response.
 * Keep these declarative, read-only, and data-grounded. Application actions
 * (analysis, approval/rejection, and profile editing) remain outside this catalog.
 */
const definitions = {
  WealthMetric: {
    description:
      "A single read-only financial metric for a value, amount, percentage, count, risk level, or time period. Values must be grounded in supplied profile or analysis data.",
    props: z.object({
      label: z.string(),
      value: z.string(),
      detail: z.string().optional(),
      tone: z.enum(["neutral", "positive", "warning", "critical"]).optional(),
    }),
  },

  WealthMetricGrid: {
    description:
      "A compact grid of 2–8 related metrics. Use for dashboards, summaries, KPIs, account snapshots, or risk overviews. Values must come from supplied data or deterministic calculations explicitly described in the answer.",
    props: z.object({
      title: z.string().optional(),
      columns: z.number().int().min(1).max(4).optional(),
      metrics: z.array(
        z.object({
          label: z.string(),
          value: z.string(),
          detail: z.string().optional(),
          tone: z
            .enum(["neutral", "positive", "warning", "critical"])
            .optional(),
        }),
      ).min(1).max(8),
    }),
  },

  WealthInsightList: {
    description:
      "A list of evidence-grounded observations or recommended discussion points. Good for risk summaries, anomalies, highlights, and prioritized next steps. Do not use it to approve actions or execute financial transactions.",
    props: z.object({
      title: z.string(),
      description: z.string().optional(),
      items: z.array(
        z.object({
          label: z.string(),
          detail: z.string().optional(),
          priority: z.string().optional(),
          evidenceId: z.string().optional(),
        }),
      ).max(20),
    }),
  },

  WealthComparisonBars: {
    description:
      "A read-only horizontal bar comparison for monthly income/expenses, portfolio holdings, categories, or scenarios. Labels, values, and units must match source data. This chart scales bars relative to the largest value.",
    props: z.object({
      title: z.string(),
      description: z.string().optional(),
      unitLabel: z.string().optional(),
      items: z.array(
        z.object({
          label: z.string(),
          value: z.number(),
          displayValue: z.string().optional(),
        }),
      ).min(1).max(24),
    }),
  },

  WealthBreakdown: {
    description:
      "A read-only proportional breakdown of categories or portfolio allocation. The renderer calculates relative shares from the numeric values; do not mix currencies or incomparable units in one breakdown.",
    props: z.object({
      title: z.string(),
      description: z.string().optional(),
      unitLabel: z.string().optional(),
      items: z.array(
        z.object({
          label: z.string(),
          value: z.number().nonnegative(),
          displayValue: z.string().optional(),
        }),
      ).min(1).max(20),
    }),
  },

  WealthTrendLine: {
    description:
      "A simple read-only line chart for ordered monthly or dated numeric observations such as income, expenses, savings, or portfolio value. Values must be explicitly present in the source data; do not invent missing periods.",
    props: z.object({
      title: z.string(),
      description: z.string().optional(),
      unitLabel: z.string().optional(),
      items: z.array(
        z.object({
          label: z.string(),
          value: z.number(),
          displayValue: z.string().optional(),
        }),
      ).min(2).max(24),
    }),
  },

  WealthMultiSeriesTrend: {
    description:
      "A read-only multi-series line chart for two or more related monthly or dated numeric series sharing the same labels, such as income, expenses, and savings. Every series must use the same unit and currency. Values must be present in source data; do not invent missing periods.",
    props: z.object({
      title: z.string(),
      description: z.string().optional(),
      unitLabel: z.string().optional(),
      labels: z.array(z.string()).min(2).max(24),
      series: z.array(
        z.object({
          name: z.string(),
          values: z.array(z.number()).min(2).max(24),
          displayValues: z.array(z.string()).optional(),
        }),
      ).min(1).max(6),
    }),
  },

  WealthDataTable: {
    description:
      "A compact read-only table for a comparison, transaction sample, goal ledger, assumptions, or evidence mapping. Use short column headings and provide each row as display-ready strings. Do not include unverified financial data.",
    props: z.object({
      title: z.string(),
      description: z.string().optional(),
      columns: z.array(z.string()).min(1).max(8),
      rows: z.array(z.array(z.string()).max(8)).max(40),
      caption: z.string().optional(),
    }),
  },

  WealthProgressList: {
    description:
      "A read-only progress display for financial goals. Supply current and target numbers and optional display labels. The component computes progress from current/target, capped visually at 100%; do not imply that an unachieved goal is guaranteed.",
    props: z.object({
      title: z.string(),
      description: z.string().optional(),
      items: z.array(
        z.object({
          label: z.string(),
          current: z.number().nonnegative(),
          target: z.number().positive(),
          currentDisplay: z.string().optional(),
          targetDisplay: z.string().optional(),
          detail: z.string().optional(),
        }),
      ).min(1).max(16),
    }),
  },

  WealthTimeline: {
    description:
      "A read-only timeline of dated goals or known events. Do not invent dates or present estimates as commitments. State clearly when a date is only a target supplied by the user.",
    props: z.object({
      title: z.string(),
      description: z.string().optional(),
      items: z.array(
        z.object({
          date: z.string(),
          label: z.string(),
          detail: z.string().optional(),
          status: z.string().optional(),
        }),
      ).max(24),
    }),
  },

  WealthCallout: {
    description:
      "A concise contextual callout for an important caveat, insight, assumption, safety note, or next-step summary. Use a truthful tone; never present a screening signal as proof of fraud or a projected return as guaranteed.",
    props: z.object({
      title: z.string(),
      body: z.string(),
      tone: z.enum(["neutral", "positive", "warning", "critical"]).optional(),
      evidenceIds: z.array(z.string()).max(8).optional(),
    }),
  },
} satisfies CatalogDefinitions;

type MetricProps = z.infer<typeof definitions.WealthMetric.props>;
type MetricGridProps = z.infer<typeof definitions.WealthMetricGrid.props>;
type InsightProps = z.infer<typeof definitions.WealthInsightList.props>;
type BarsProps = z.infer<typeof definitions.WealthComparisonBars.props>;
type BreakdownProps = z.infer<typeof definitions.WealthBreakdown.props>;
type TrendProps = z.infer<typeof definitions.WealthTrendLine.props>;
type MultiSeriesTrendProps = z.infer<
  typeof definitions.WealthMultiSeriesTrend.props
>;
type TableProps = z.infer<typeof definitions.WealthDataTable.props>;
type ProgressProps = z.infer<typeof definitions.WealthProgressList.props>;
type TimelineProps = z.infer<typeof definitions.WealthTimeline.props>;
type CalloutProps = z.infer<typeof definitions.WealthCallout.props>;

function Metric({
  label,
  value,
  detail,
  tone = "neutral",
}: MetricProps) {
  return (
    <article className={`a2ui-metric a2ui-${tone}`}>
      <span className="a2ui-label">{label}</span>
      <strong>{value}</strong>
      {detail ? <small>{detail}</small> : null}
    </article>
  );
}

function MetricGrid({
  title,
  columns = 2,
  metrics,
}: MetricGridProps) {
  return (
    <section className="a2ui-panel">
      {title ? <h3>{title}</h3> : null}

      <div
        className="a2ui-metric-grid"
        style={{
          gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))`,
        }}
      >
        {metrics.map((metric, index) => (
          <Metric key={`${metric.label}-${index}`} {...metric} />
        ))}
      </div>
    </section>
  );
}

function InsightList({
  title,
  description,
  items,
}: InsightProps) {
  return (
    <section className="a2ui-panel">
      <h3>{title}</h3>
      {description ? <p className="a2ui-muted">{description}</p> : null}

      <ul className="a2ui-insights">
        {items.map((item, index) => (
          <li key={`${item.label}-${index}`}>
            <div className="a2ui-insight-heading">
              <strong>{item.label}</strong>
              {item.priority ? (
                <span className="a2ui-priority">{item.priority}</span>
              ) : null}
            </div>

            {item.detail ? <p>{item.detail}</p> : null}

            {item.evidenceId ? (
              <small className="a2ui-evidence">
                Evidence: {item.evidenceId}
              </small>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

function ComparisonBars({
  title,
  description,
  unitLabel,
  items,
}: BarsProps) {
  const max = Math.max(
    1,
    ...items.map((item) => Math.max(0, item.value)),
  );

  return (
    <section className="a2ui-panel">
      <h3>{title}</h3>
      {description ? <p className="a2ui-muted">{description}</p> : null}
      {unitLabel ? <p className="a2ui-muted">Units: {unitLabel}</p> : null}

      <div className="a2ui-bars">
        {items.map((item, index) => (
          <div
            className="a2ui-bar-row"
            key={`${item.label}-${index}`}
          >
            <div className="a2ui-bar-top">
              <span>{item.label}</span>
              <strong>
                {item.displayValue ?? item.value.toLocaleString()}
              </strong>
            </div>

            <div className="a2ui-track">
              <span
                style={{
                  width: `${
                    Math.max(
                      0,
                      Math.min(100, (item.value / max) * 100),
                    )
                  }%`,
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function Breakdown({
  title,
  description,
  unitLabel,
  items,
}: BreakdownProps) {
  const total = items.reduce((sum, item) => sum + item.value, 0);

  return (
    <section className="a2ui-panel">
      <h3>{title}</h3>
      {description ? <p className="a2ui-muted">{description}</p> : null}
      {unitLabel ? <p className="a2ui-muted">Units: {unitLabel}</p> : null}

      <div className="a2ui-bars">
        {items.map((item, index) => {
          const share = total > 0 ? (item.value / total) * 100 : 0;

          return (
            <div
              className="a2ui-bar-row"
              key={`${item.label}-${index}`}
            >
              <div className="a2ui-bar-top">
                <span>{item.label}</span>
                <strong>
                  {item.displayValue ?? `${share.toFixed(1)}%`}
                </strong>
              </div>

              <div className="a2ui-track">
                <span
                  style={{
                    width: `${Math.max(0, Math.min(100, share))}%`,
                  }}
                />
              </div>
            </div>
          );
        })}
      </div>

      <p className="a2ui-footnote">
        {total > 0
          ? `Share of displayed total: ${total.toLocaleString()}.`
          : "No positive values to calculate shares."}
      </p>
    </section>
  );
}

function TrendLine({
  title,
  description,
  unitLabel,
  items,
}: TrendProps) {
  const values = items.map((item) => item.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const points = items.map((item, index) => {
    const x = items.length === 1
      ? 200
      : 12 + (index * 376) / (items.length - 1);

    const y = 126 - ((item.value - min) / range) * 104;
    return { ...item, x, y };
  });

  return (
    <section className="a2ui-panel">
      <h3>{title}</h3>
      {description ? <p className="a2ui-muted">{description}</p> : null}
      {unitLabel ? <p className="a2ui-muted">Units: {unitLabel}</p> : null}

      <div className="a2ui-line-chart">
        <svg
          viewBox="0 0 400 150"
          role="img"
          aria-label={title}
          preserveAspectRatio="none"
        >
          {[22, 74, 126].map((y) => (
            <line
              key={y}
              x1="8"
              y1={y}
              x2="392"
              y2={y}
              className="a2ui-grid-line"
            />
          ))}

          <polyline
            points={points.map((point) => `${point.x},${point.y}`).join(" ")}
            className="a2ui-line"
          />

          {points.map((point, index) => (
            <circle
              key={`${point.label}-${index}`}
              cx={point.x}
              cy={point.y}
              r="3.5"
              className="a2ui-point"
            >
              <title>
                {`${point.label}: ${point.displayValue ?? point.value}`}
              </title>
            </circle>
          ))}
        </svg>

        <div className="a2ui-line-labels">
          {points.map((point, index) => (
            <div key={`${point.label}-${index}`}>
              <strong>
                {point.displayValue ?? point.value.toLocaleString()}
              </strong>
              <span>{point.label}</span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function MultiSeriesTrend({
  title,
  description,
  unitLabel,
  labels,
  series,
}: MultiSeriesTrendProps) {
  const allValues = series.flatMap((entry) =>
    entry.values.slice(0, labels.length).filter(Number.isFinite),
  );

  const min = Math.min(0, ...allValues);
  const max = Math.max(1, ...allValues);
  const range = max - min || 1;

  const xFor = (index: number) =>
    labels.length === 1 ? 200 : 16 + (index * 368) / (labels.length - 1);

  const yFor = (value: number) => 124 - ((value - min) / range) * 100;

  return (
    <section className="a2ui-panel">
      <h3>{title}</h3>
      {description ? <p className="a2ui-muted">{description}</p> : null}
      {unitLabel ? <p className="a2ui-muted">Units: {unitLabel}</p> : null}

      <div className="a2ui-multi-trend">
        <svg
          viewBox="0 0 400 145"
          role="img"
          aria-label={title}
          preserveAspectRatio="none"
        >
          {[24, 74, 124].map((y) => (
            <line
              key={y}
              x1="8"
              y1={y}
              x2="392"
              y2={y}
              className="a2ui-grid-line"
            />
          ))}

          {series.map((entry, seriesIndex) => {
            const points = entry.values
              .slice(0, labels.length)
              .map((value, index) => ({
                x: xFor(index),
                y: yFor(value),
                value,
                label: labels[index],
                displayValue: entry.displayValues?.[index],
              }))
              .filter((point) => Number.isFinite(point.value));

            if (points.length < 2) return null;

            return (
              <g key={`${entry.name}-${seriesIndex}`}>
                <polyline
                  className={`a2ui-multi-line a2ui-series-${seriesIndex}`}
                  points={points
                    .map((point) => `${point.x},${point.y}`)
                    .join(" ")}
                />

                {points.map((point, pointIndex) => (
                  <circle
                    key={`${point.label}-${pointIndex}`}
                    className={`a2ui-multi-point a2ui-series-${seriesIndex}`}
                    cx={point.x}
                    cy={point.y}
                    r="3"
                  >
                    <title>
                      {`${entry.name} · ${point.label}: ${
                        point.displayValue ?? point.value.toLocaleString()
                      }`}
                    </title>
                  </circle>
                ))}
              </g>
            );
          })}
        </svg>

        <div className="a2ui-multi-legend">
          {series.map((entry, index) => (
            <span key={`${entry.name}-${index}`}>
              <i className={`a2ui-series-swatch a2ui-series-${index}`} />
              {entry.name}
            </span>
          ))}
        </div>

        <div className="a2ui-multi-labels">
          {labels.map((label, index) => (
            <span key={`${label}-${index}`}>{label}</span>
          ))}
        </div>

        <div className="a2ui-multi-values">
          {series.map((entry, seriesIndex) => (
            <div key={`${entry.name}-${seriesIndex}`}>
              <strong>{entry.name}</strong>
              <span>
                {entry.values
                  .slice(0, labels.length)
                  .map(
                    (value, index) =>
                      `${labels[index]}: ${
                        entry.displayValues?.[index] ?? value.toLocaleString()
                      }`,
                  )
                  .join(" · ")}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function DataTable({
  title,
  description,
  columns,
  rows,
  caption,
}: TableProps) {
  return (
    <section className="a2ui-panel">
      <h3>{title}</h3>
      {description ? <p className="a2ui-muted">{description}</p> : null}

      <div className="a2ui-table-wrap">
        <table className="a2ui-table">
          <thead>
            <tr>
              {columns.map((column, index) => (
                <th key={`${column}-${index}`}>{column}</th>
              ))}
            </tr>
          </thead>

          <tbody>
            {rows.map((row, rowIndex) => (
              <tr key={`row-${rowIndex}`}>
                {columns.map((column, columnIndex) => (
                  <td key={`${column}-${columnIndex}`}>
                    {row[columnIndex] ?? "—"}
                  </td>
                ))}
              </tr>
            ))}

            {rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length}>
                  No rows available in the supplied data.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>

      {caption ? <p className="a2ui-footnote">{caption}</p> : null}
    </section>
  );
}

function ProgressList({
  title,
  description,
  items,
}: ProgressProps) {
  return (
    <section className="a2ui-panel">
      <h3>{title}</h3>
      {description ? <p className="a2ui-muted">{description}</p> : null}

      <div className="a2ui-progress-list">
        {items.map((item, index) => {
          const progress = Math.max(
            0,
            Math.min(100, (item.current / item.target) * 100),
          );

          return (
            <div
              className="a2ui-progress-item"
              key={`${item.label}-${index}`}
            >
              <div className="a2ui-bar-top">
                <span>{item.label}</span>
                <strong>{progress.toFixed(1)}%</strong>
              </div>

              <div className="a2ui-track">
                <span style={{ width: `${progress}%` }} />
              </div>

              <div className="a2ui-progress-values">
                <span>
                  {item.currentDisplay ?? item.current.toLocaleString()}
                </span>
                <span>
                  Target {item.targetDisplay ?? item.target.toLocaleString()}
                </span>
              </div>

              {item.detail ? <p>{item.detail}</p> : null}
            </div>
          );
        })}
      </div>

      <p className="a2ui-footnote">
        Progress is a snapshot from the supplied values, not a guarantee
        of reaching a goal.
      </p>
    </section>
  );
}

function Timeline({
  title,
  description,
  items,
}: TimelineProps) {
  return (
    <section className="a2ui-panel">
      <h3>{title}</h3>
      {description ? <p className="a2ui-muted">{description}</p> : null}

      <ol className="a2ui-timeline">
        {items.map((item, index) => (
          <li key={`${item.date}-${item.label}-${index}`}>
            <time>{item.date}</time>
            <strong>{item.label}</strong>

            {item.status ? (
              <span className="a2ui-timeline-status">
                {item.status}
              </span>
            ) : null}

            {item.detail ? <p>{item.detail}</p> : null}
          </li>
        ))}
      </ol>
    </section>
  );
}

function Callout({
  title,
  body,
  tone = "neutral",
  evidenceIds = [],
}: CalloutProps) {
  return (
    <aside className={`a2ui-callout a2ui-callout-${tone}`}>
      <strong>{title}</strong>
      <p>{body}</p>

      {evidenceIds.length ? (
        <div className="a2ui-evidence-list">
          {evidenceIds.map((id) => (
            <span key={id}>{id}</span>
          ))}
        </div>
      ) : null}
    </aside>
  );
}

// CopilotKit A2UI renderer functions receive an envelope with a `props` field,
// not the domain props directly. Keep the presentation components above simple,
// and adapt the envelope here so the catalog matches ComponentRenderer's API.
const renderers: CatalogRenderers<typeof definitions> = {
  WealthMetric: ({ props }) => <Metric {...props} />,
  WealthMetricGrid: ({ props }) => <MetricGrid {...props} />,
  WealthInsightList: ({ props }) => <InsightList {...props} />,
  WealthComparisonBars: ({ props }) => <ComparisonBars {...props} />,
  WealthBreakdown: ({ props }) => <Breakdown {...props} />,
  WealthTrendLine: ({ props }) => <TrendLine {...props} />,
  WealthMultiSeriesTrend: ({ props }) => <MultiSeriesTrend {...props} />,
  WealthDataTable: ({ props }) => <DataTable {...props} />,
  WealthProgressList: ({ props }) => <ProgressList {...props} />,
  WealthTimeline: ({ props }) => <Timeline {...props} />,
  WealthCallout: ({ props }) => <Callout {...props} />,
};

export const wealthAdvisorCatalog = createCatalog(definitions, renderers, {
  catalogId: "wealth-advisor-catalog",
  // Standard components such as Row, Column, Card, Tabs, Text, and List can be
  // combined with the wealth-specific renderers for a much more expressive UI.
  includeBasicCatalog: true,
});

export type A2UIChild = ReactNode;