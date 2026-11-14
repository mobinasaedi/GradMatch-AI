import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { STATUS_LABELS } from "../api";
import { band, dateTime, initials, relative, shortDate } from "../lib/format";
import { Button, Card, CountryTag, EmptyState, Icon, Meter, Ring, SectionHead, StatTile } from "../ui";

const FUNNEL_ORDER = ["draft_ready", "sent", "follow_up_needed", "replied", "closed"];
const FUNNEL_COLORS = ["#818CF8", "#22D3EE", "#FBBF24", "#34D399", "#94A3B8"];

function ChartTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tip">
      <strong>{label}</strong>
      {payload.map((entry) => (
        <span key={entry.dataKey}>
          {entry.name}: {entry.value}
        </span>
      ))}
    </div>
  );
}

export default function Dashboard({ student, run, overview, runs, meta, onNavigate, onOpenRun }) {
  if (!student) {
    return (
      <Card className="empty-card">
        <EmptyState
          icon="file"
          title="Start with your resume"
          hint="Upload a PDF or DOCX. The extractor turns it into an editable research profile, and nothing leaves your machine."
          action={
            <Button variant="primary" icon="arrowRight" onClick={() => onNavigate("profile")}>
              Upload resume
            </Button>
          }
        />
      </Card>
    );
  }

  const hasRun = Boolean(run?.results?.length);
  const best = hasRun ? run.results[0] : null;
  const bestBand = best ? band(best.fit) : null;
  const completeness = overview?.profile_completeness ?? 0;
  const buckets = overview?.score_buckets || [];
  const activity = overview?.activity || [];
  const funnelRows = FUNNEL_ORDER.map((key, index) => ({
    key,
    label: STATUS_LABELS[key],
    count: overview?.funnel?.[key] || 0,
    color: FUNNEL_COLORS[index],
  }));
  const maxFunnel = Math.max(1, ...funnelRows.map((row) => row.count));

  return (
    <div className="dash">
      <Card className="dash-hero">
        <div className="dash-hero-copy">
          <p className="eyebrow">Research fit</p>
          <h2>
            {hasRun ? (
              <>
                Your strongest match today is{" "}
                <span className="grad-text">{best.professor.name}</span>
              </>
            ) : (
              <>
                Your profile is ready. Let&apos;s find <span className="grad-text">supervisors</span>.
              </>
            )}
          </h2>
          <p className="hint">
            {hasRun ? (
              <>
                {best.professor.institution_name} · {bestBand.label} · seen {relative(run.created_at)}
              </>
            ) : (
              "Choose the countries you care about and the matcher will rank researchers from their recent publications."
            )}
          </p>
          <div className="dash-hero-actions">
            <Button variant="primary" icon="compass" onClick={() => onNavigate("search")}>
              {hasRun ? "Run a new search" : "Find supervisors"}
            </Button>
            {hasRun && (
              <Button variant="ghost" icon="sparkles" onClick={() => onNavigate("matches")}>
                Open shortlist
              </Button>
            )}
          </div>
        </div>
        <div className="dash-hero-side">
          <Ring value={hasRun ? best.fit : completeness} size={104} stroke={8} />
          <p className="tiny">{hasRun ? "top match fit" : "profile completeness"}</p>
          <div className="dash-hero-mini">
            <span>
              <Icon name="database" size={13} /> {meta?.counts?.professors ?? 0} indexed
            </span>
            <span>
              <Icon name="clock" size={13} /> {overview?.runs ?? 0} searches
            </span>
          </div>
        </div>
      </Card>

      <div className="stat-row">
        <StatTile
          label="Matches"
          value={overview?.matches ?? 0}
          icon="sparkles"
          foot={hasRun ? `across ${overview?.universities?.length || 0} universities` : "no search yet"}
        />
        <StatTile
          label="Average fit"
          value={overview?.avg_fit ?? 0}
          suffix="/100"
          icon="target"
          tone="violet"
          foot={`best ${overview?.best_fit ?? 0}`}
        />
        <StatTile
          label="Contacted"
          value={overview?.contacted ?? 0}
          icon="mail"
          tone="cyan"
          foot={`${overview?.replies ?? 0} replies · ${overview?.reply_rate ?? 0}%`}
        />
        <StatTile
          label="Profile"
          value={completeness}
          suffix="%"
          icon="user"
          tone="emerald"
          foot={completeness === 100 ? "complete" : "add the missing fields"}
        />
      </div>

      <div className="dash-charts">
        <Card>
          <SectionHead eyebrow="Distribution" title="Fit spread of the shortlist" />
          {hasRun ? (
            <div className="chart">
              <ResponsiveContainer width="100%" height={210}>
                <BarChart data={buckets} margin={{ top: 8, right: 8, left: -18, bottom: 0 }}>
                  <CartesianGrid stroke="rgba(255,255,255,.07)" vertical={false} />
                  <XAxis dataKey="label" tick={{ fill: "#8b96b8", fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: "#8b96b8", fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                  <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(255,255,255,.04)" }} />
                  <Bar dataKey="count" name="professors" radius={[6, 6, 0, 0]}>
                    {buckets.map((entry, index) => (
                      <Cell key={entry.label} fill={["#475569", "#6366F1", "#8B5CF6", "#22D3EE"][index % 4]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <p className="chart-empty">Run a search to see how the shortlist spreads across fit bands.</p>
          )}
        </Card>

        <Card>
          <SectionHead eyebrow="Overlap" title="Topics shared with your shortlist" />
          {overview?.top_topics?.length ? (
            <ul className="topic-list">
              {overview.top_topics.map((topic) => (
                <li key={topic.label}>
                  <div className="topic-row">
                    <span>{topic.label}</span>
                    <span className="tiny">{topic.count}</span>
                  </div>
                  <Meter value={(topic.count / Math.max(...overview.top_topics.map((t) => t.count))) * 100} />
                </li>
              ))}
            </ul>
          ) : (
            <p className="chart-empty">Shared research topics appear here after your first search.</p>
          )}
        </Card>
      </div>

      <div className="dash-charts">
        <Card>
          <SectionHead eyebrow="Outreach" title="Pipeline" action={<Button variant="ghost" className="btn-sm" onClick={() => onNavigate("outreach")}>Open tracker</Button>} />
          <ul className="funnel">
            {funnelRows.map((row) => (
              <li key={row.key}>
                <span className="funnel-label">{row.label}</span>
                <span className="funnel-track">
                  <span
                    className="funnel-fill"
                    style={{ width: `${Math.max(3, (row.count / maxFunnel) * 100)}%`, background: row.color }}
                  />
                </span>
                <span className="funnel-value">{row.count}</span>
              </li>
            ))}
          </ul>
        </Card>

        <Card>
          <SectionHead eyebrow="Last 14 days" title="Activity" />
          <div className="chart">
            <ResponsiveContainer width="100%" height={190}>
              <AreaChart data={activity} margin={{ top: 8, right: 8, left: -22, bottom: 0 }}>
                <defs>
                  <linearGradient id="activityFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#8B5CF6" stopOpacity={0.5} />
                    <stop offset="100%" stopColor="#8B5CF6" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid stroke="rgba(255,255,255,.07)" vertical={false} />
                <XAxis
                  dataKey="date"
                  tickFormatter={(value) => new Date(value).toLocaleDateString(undefined, { day: "2-digit", month: "short" })}
                  tick={{ fill: "#8b96b8", fontSize: 10 }}
                  axisLine={false}
                  tickLine={false}
                  interval="preserveStartEnd"
                  minTickGap={28}
                />
                <YAxis tick={{ fill: "#8b96b8", fontSize: 10 }} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip content={<ChartTooltip />} />
                <Area type="monotone" dataKey="events" name="status changes" stroke="#A78BFA" strokeWidth={2} fill="url(#activityFill)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </Card>
      </div>

      <div className="dash-lists">
        <Card>
          <SectionHead
            eyebrow="Shortlist"
            title="Top candidates"
            action={
              hasRun ? (
                <Button variant="ghost" className="btn-sm" onClick={() => onNavigate("matches")}>
                  See all
                </Button>
              ) : null
            }
          />
          {hasRun ? (
            <ul className="mini-list">
              {run.results.slice(0, 4).map((item) => (
                <li key={item.professor.id}>
                  <span className="avatar">{initials(item.professor.name)}</span>
                  <div className="mini-main">
                    <strong>{item.professor.name}</strong>
                    <span className="tiny">
                      <CountryTag code={item.professor.country_code} /> {item.professor.institution_name}
                    </span>
                  </div>
                  <span className={`fit-pill fit-${band(item.fit).key}`}>{Math.round(item.fit)}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="chart-empty">No shortlist yet.</p>
          )}
        </Card>

        <Card>
          <SectionHead eyebrow="History" title="Past searches" />
          {runs?.length ? (
            <ul className="run-list">
              {runs.slice(0, 4).map((entry) => (
                <li key={entry.run_id}>
                  <button className="run-row" onClick={() => onOpenRun(entry.run_id)}>
                    <span className="run-main">
                      <strong>
                        {entry.university_names?.slice(0, 2).join(", ") || "Search"}{" "}
                        {entry.university_names?.length > 2 ? `+${entry.university_names.length - 2}` : ""}
                      </strong>
                      <span className="tiny">
                        {dateTime(entry.created_at)} · {entry.results_count} results · avg fit {entry.avg_fit}
                      </span>
                    </span>
                    <Icon name="chevronRight" size={16} />
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="chart-empty">Your searches are stored in the database and listed here.</p>
          )}
        </Card>

        <Card>
          <SectionHead eyebrow="Data layer" title="Database" action={<span className="pill pill-muted">{meta?.database_dialect || "sqlite"}</span>} />
          <ul className="table-stats">
            {(meta?.tables || []).slice(0, 6).map((table) => (
              <li key={table.table}>
                <span>{table.table.replace(/_/g, " ")}</span>
                <strong>{table.rows}</strong>
              </li>
            ))}
          </ul>
          <p className="tiny">
            {meta?.demo_seeded ? "Bundled dataset loaded" : "Dataset not loaded"} · seed from{" "}
            <code>data/raw</code>
          </p>
        </Card>
      </div>

      <Card className="dash-footer-card">
        <div className="row-between">
          <div>
            <p className="eyebrow">Since your last search</p>
            <p className="hint">
              {run ? (
                <>
                  Shortlist generated {shortDate(run.created_at)} with the <strong>{run.backend}</strong> scorer
                  {run.params?.university_names?.length ? ` over ${run.params.university_names.join(", ")}` : ""}.
                </>
              ) : (
                "Nothing yet — one search produces ten candidates in a few seconds with the bundled dataset."
              )}
            </p>
          </div>
          <Button variant="ghost" icon="key" onClick={() => onNavigate("setup")}>
            API keys
          </Button>
        </div>
      </Card>
    </div>
  );
}
