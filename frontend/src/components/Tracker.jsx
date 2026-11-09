import { Fragment, useCallback, useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, STATUS_LABELS } from "../api";

export default function Tracker({ student }) {
  const [rows, setRows] = useState([]);
  const [stats, setStats] = useState(null);
  const [events, setEvents] = useState({});
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    try {
      const [o, s] = await Promise.all([api.outreach(student.id), api.outreachStats(student.id)]);
      setRows(o);
      setStats(s);
    } catch (e) {
      setError(e.message);
    }
  }, [student.id]);

  useEffect(() => {
    load();
  }, [load]);

  const update = async (id, data) => {
    await api.updateOutreach(id, data);
    load();
  };

  const toggleHistory = async (id) => {
    if (events[id]) {
      setEvents((e) => ({ ...e, [id]: null }));
      return;
    }
    const list = await api.outreachEvents(id);
    setEvents((e) => ({ ...e, [id]: list }));
  };

  const chartData = stats
    ? Object.entries(stats.by_status).map(([k, v]) => ({ status: STATUS_LABELS[k], count: v }))
    : [];

  if (error) return <p className="error">{error}</p>;
  if (rows.length === 0) return <section className="card"><p>Nothing to track yet: get recommendations first.</p></section>;

  return (
    <div>
      <section className="card">
        <h2>Outreach overview</h2>
        <div style={{ height: 220 }}>
          <ResponsiveContainer>
            <BarChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="status" tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill="#3b6ef5" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="card">
        <h2>Professors</h2>
        <p className="muted">Update the status yourself after each action (the MVP does not read or send email).</p>
        <table>
          <thead>
            <tr><th>Professor</th><th>University</th><th>Status</th><th>Notes</th><th></th></tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <Fragment key={r.id}>
                <tr>
                  <td>{r.professor.name}</td>
                  <td>{r.professor.institution_name}</td>
                  <td>
                    <select value={r.status} onChange={(e) => update(r.id, { status: e.target.value })}>
                      {Object.entries(STATUS_LABELS).map(([value, label]) => (
                        <option key={value} value={value}>{label}</option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input defaultValue={r.notes || ""} placeholder="Add a note"
                      onBlur={(e) => e.target.value !== (r.notes || "") && update(r.id, { notes: e.target.value })} />
                  </td>
                  <td><button className="link" onClick={() => toggleHistory(r.id)}>History</button></td>
                </tr>
                {events[r.id] && (
                  <tr>
                    <td colSpan={5}>
                      <ul className="history">
                        {events[r.id].map((ev) => (
                          <li key={ev.id}>
                            {new Date(ev.created_at).toLocaleString()} — {STATUS_LABELS[ev.status] || ev.status}
                            {ev.note ? `: ${ev.note}` : ""}
                          </li>
                        ))}
                        {events[r.id].length === 0 && <li className="muted">No changes yet.</li>}
                      </ul>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  );
}
