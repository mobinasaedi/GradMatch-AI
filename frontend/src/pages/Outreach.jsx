import { useCallback, useEffect, useMemo, useState } from "react";
import { api, STATUS_LABELS, STATUS_ORDER } from "../api";
import { dateTime, initials, relative } from "../lib/format";
import { Badge, Button, Card, CountryTag, EmptyState, Icon, SectionHead, StatTile } from "../ui";

export default function Outreach({ student, notify, onNavigate }) {
  const [rows, setRows] = useState([]);
  const [stats, setStats] = useState(null);
  const [events, setEvents] = useState({});
  const [filter, setFilter] = useState("all");
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);

  const load = useCallback(async () => {
    if (!student) return;
    try {
      const [list, summary] = await Promise.all([api.outreach(student.id), api.outreachStats(student.id)]);
      setRows(list);
      setStats(summary);
    } catch (e) {
      setError(e.message);
    }
  }, [student]);

  useEffect(() => {
    load();
  }, [load]);

  const update = async (id, data) => {
    setBusyId(id);
    try {
      await api.updateOutreach(id, data);
      await load();
      notify("Tracker updated", "success");
    } catch (e) {
      notify(e.message, "error");
    } finally {
      setBusyId(null);
    }
  };

  const toggleHistory = async (id) => {
    if (events[id]) {
      setEvents((current) => ({ ...current, [id]: null }));
      return;
    }
    const list = await api.outreachEvents(id);
    setEvents((current) => ({ ...current, [id]: list }));
  };

  const filtered = useMemo(
    () => (filter === "all" ? rows : rows.filter((row) => row.status === filter)),
    [rows, filter],
  );

  if (!student) {
    return (
      <Card>
        <EmptyState
          icon="mail"
          title="Nothing to track yet"
          hint="Generate a shortlist first — every matched professor is added to this tracker automatically."
          action={
            <Button variant="primary" onClick={() => onNavigate("search")}>
              Find supervisors
            </Button>
          }
        />
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <p className="form-error">{error}</p>
      </Card>
    );
  }

  return (
    <div className="stack">
      <div className="stat-row">
        <StatTile label="In tracker" value={stats?.total ?? 0} icon="mail" />
        <StatTile
          label="Sent"
          value={stats?.by_status?.sent ?? 0}
          icon="arrowRight"
          tone="cyan"
          foot="waiting for a reply"
        />
        <StatTile
          label="Replied"
          value={stats?.by_status?.replied ?? 0}
          icon="check"
          tone="emerald"
          foot={`${stats?.by_status?.follow_up_needed ?? 0} pending follow-up`}
        />
        <StatTile
          label="Closed"
          value={stats?.by_status?.closed ?? 0}
          icon="flag"
          tone="violet"
          foot="archived conversations"
        />
      </div>

      <Card>
        <SectionHead
          eyebrow="Pipeline"
          title="Contacts"
          hint="The app never sends mail: you write, copy, send from your own client, then record what happened."
        />
        <div className="filter-row">
          <button className={`seg ${filter === "all" ? "active" : ""}`} onClick={() => setFilter("all")}>
            All {rows.length}
          </button>
          {STATUS_ORDER.map((status) => (
            <button
              key={status}
              className={`seg ${filter === status ? "active" : ""}`}
              onClick={() => setFilter(status)}
            >
              {STATUS_LABELS[status]}
            </button>
          ))}
        </div>

        {rows.length === 0 ? (
          <EmptyState
            icon="mail"
            title="The tracker is empty"
            hint="Run a search; each candidate is inserted here with status “not started”."
            action={
              <Button variant="primary" onClick={() => onNavigate("search")}>
                Run a search
              </Button>
            }
          />
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Professor</th>
                  <th>University</th>
                  <th>Status</th>
                  <th>Notes</th>
                  <th>Updated</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {filtered.map((row) => (
                  <tr key={row.id}>
                    <td>
                      <div className="cell-person">
                        <span className="avatar avatar-sm">{initials(row.professor.name)}</span>
                        <div>
                          <strong>{row.professor.name}</strong>
                          <span className="tiny">
                            {row.professor.email ? (
                              <a href={`mailto:${row.professor.email}`}>{row.professor.email}</a>
                            ) : (
                              "no email stored"
                            )}
                          </span>
                        </div>
                      </div>
                    </td>
                    <td className="tiny">
                      <CountryTag code={row.professor.country_code} /> {row.professor.institution_name}
                    </td>
                    <td>
                      <select
                        className={`status-select status-${row.status}`}
                        value={row.status}
                        disabled={busyId === row.id}
                        onChange={(event) => update(row.id, { status: event.target.value })}
                      >
                        {STATUS_ORDER.map((status) => (
                          <option key={status} value={status}>
                            {STATUS_LABELS[status]}
                          </option>
                        ))}
                      </select>
                    </td>
                    <td>
                      <input
                        className="note-input"
                        defaultValue={row.notes || ""}
                        placeholder="Add a note"
                        onBlur={(event) =>
                          event.target.value !== (row.notes || "") && update(row.id, { notes: event.target.value })
                        }
                      />
                    </td>
                    <td className="tiny">{relative(row.updated_at)}</td>
                    <td>
                      <Button variant="ghost" className="btn-sm" onClick={() => toggleHistory(row.id)}>
                        {events[row.id] ? "Hide" : "History"}
                      </Button>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 && (
                  <tr>
                    <td colSpan={6} className="tiny center">
                      Nothing with this status.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {Object.entries(events).some(([, value]) => value) && (
        <Card className="soft">
          <SectionHead eyebrow="Audit trail" title="Status history" />
          <ul className="timeline">
            {Object.entries(events)
              .filter(([, value]) => value)
              .flatMap(([id, list]) =>
                list.map((event) => {
                  const row = rows.find((item) => String(item.id) === String(id));
                  return (
                    <li key={`${id}-${event.id}`}>
                      <span className={`timeline-dot dot-${event.status}`} />
                      <div>
                        <strong>{row?.professor?.name || "Professor"}</strong>{" "}
                        <Badge tone="neutral">{STATUS_LABELS[event.status] || event.status}</Badge>
                        {event.note ? <span className="tiny"> — {event.note}</span> : null}
                        <span className="tiny block">{dateTime(event.created_at)}</span>
                      </div>
                    </li>
                  );
                }),
              )}
          </ul>
        </Card>
      )}
    </div>
  );
}
