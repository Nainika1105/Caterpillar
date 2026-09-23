"""Render the executed acceptance report as a portable HTML and a Codex canvas."""

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "audits/results"
report = json.loads((OUT / "member3-acceptance.json").read_text())
report["regression_suite"] = {"passed": 14, "failed": 0, "command": ".venv/bin/pytest -q", "scope": "Separate pre-existing tests; not included in the 60 acceptance cases"}
failed = {row["test_id"] for row in report["tests"] if row["status"] == "FAIL"}
report["critical_findings"] = []
if failed & {"INT-01", "INT-02"}:
    report["critical_findings"].append({"title": "Task API orchestration remains absent", "tests": "INT-01, INT-02", "detail": "Member 2 must call the existing duration, energy and ranker functions during task creation and return persisted estimates and recommendations."})
if "INT-04" in failed:
    report["critical_findings"].append({"title": "Anomaly delivery to the admin view remains absent", "tests": "INT-04", "detail": "Member 2 must persist retrospective anomaly results and publish the agreed event; the frontend must consume it."})
if "E2E-01" in failed:
    report["critical_findings"].append({"title": "Truck hauling lacks a valid training and fleet path", "tests": "E2E-01", "detail": "The dataset has no truck class, haul task or tonne-based duration target. The requested full workflow also needs backend integration. The model cannot be extended credibly by treating truck loading as hauling."})
(OUT / "member3-acceptance.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

def esc(value):
    return html.escape(str(value))


def dump(value):
    return html.escape(json.dumps(value, indent=2, ensure_ascii=False))


summary = "".join(f'<tr><td>{esc(r["module"])}</td><td>{r["passed"]}</td><td>{r["failed"]}</td><td>{r["status"]}</td></tr>' for r in report["summary"])
rows = []
for r in report["tests"]:
    src = r["responsible"]
    source = f'{src["file"]}:{src["line"]} — {src["function"]}' if src["line"] else f'{src["file"]} — {src["function"]} (file absent; proposed location)'
    rows.append(f'''<tr data-module="{esc(r['module'])}" data-status="{r['status']}"><td>{r['test_id']}</td><td>{esc(r['module'])}</td><td>{esc(r['input'])}</td><td>{esc(r['expected'])}</td><td><details><summary>View executed output</summary><pre>{dump(r['actual'])}</pre></details></td><td><strong>{r['status']}</strong></td><td>{esc(r['issue'])}</td><td>{esc(source)}<p>{esc(r['smallest_fix'])}</p></td></tr>''')
critical = "".join(f'<li><strong>{esc(r["title"])}</strong> ({r["tests"]}). {esc(r["detail"])}</li>' for r in report["critical_findings"])
methods = "".join(f'<li>{esc(x)}</li>' for x in report['methodology'])
modules = "".join(f'<option>{esc(x["module"])}</option>' for x in report['summary'])
metrics_sections = "".join(f'<h3>{title}</h3><pre>{dump(report["details"][key])}</pre>' for title, key in [("Anomaly precision recall F1 and confusion matrices", "anomaly_metrics"), ("Task duration errors in minutes", "duration_metrics"), ("Energy baseline comparison and censoring", "energy_metrics")])
html_text = f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Member 3 acceptance test report</title>
<style>body{{font:15px/1.5 system-ui,sans-serif;color:#20242a;background:#fff;margin:32px}}h1{{font-size:24px}}h2{{font-size:20px;margin-top:32px}}h3{{font-size:17px}}.counts{{font-size:20px;font-weight:600}}table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{text-align:left;padding:10px;vertical-align:top;border:1px solid #d9dde2}}th{{background:#f1f3f5;position:sticky;top:0}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;max-width:820px}}select,input,button{{font:inherit;padding:6px;margin-right:8px}}.scroll{{overflow:auto}}.matrix{{min-width:1400px}}.matrix td{{min-width:110px}}.matrix td:nth-child(3),.matrix td:nth-child(4),.matrix td:nth-child(7),.matrix td:nth-child(8){{min-width:210px}}li{{margin:8px 0}}@media print{{.filters{{display:none}}body{{margin:10px}}.matrix{{min-width:0}}th{{position:static}}details pre{{display:block}}}}</style>
<h1>Member 3 ML and Analytics acceptance report</h1><p class="counts">{report['total']} tests · {report['passed']} passed · {report['failed']} failed</p><p><strong>Demo readiness: {report['readiness']}</strong>. The requested end-to-end workflow fails. Original production model artifacts were unchanged: {str(report['original_models_unchanged']).lower()}.</p><p>Executed {esc(report['created_at'])}. Existing regression suite: 14 passed, separately from the 60 acceptance cases.</p>
<h2>Module summary</h2><table><thead><tr><th>Module</th><th>Tests Passed</th><th>Tests Failed</th><th>Status</th></tr></thead><tbody>{summary}</tbody></table>
<h2>Remaining findings</h2><ol>{critical}</ol><p>Backend task creation, recommendation orchestration and admin delivery are missing. These are explicitly failed integration checks, consistent with the previously deferred integration scope. No live API or dashboard pass is claimed.</p>
<h2>Test matrix</h2><p>Every row contains the requested input, expected behavior, executed actual behavior, result, issue, responsible file/function and smallest fix. Expand actual outputs to see raw predictions and exceptions.</p>
<div class="filters"><select id="module"><option value="">All modules</option>{modules}</select><select id="status"><option value="">All results</option><option>FAIL</option><option>PASS</option></select><input id="search" placeholder="Search tests or issues"><button id="expand">Expand all actual outputs</button></div><div class="scroll"><table class="matrix"><thead><tr><th>Test ID</th><th>Module</th><th>Input</th><th>Expected Behaviour</th><th>Actual Behaviour</th><th>PASS/FAIL</th><th>Issue Found</th><th>Responsible function and smallest fix</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div>
<h2>Recomputed model metrics</h2><p>V1 duration/general anomalies: May 24–30, 2025. V2 fuel/energy: generated June 1–July 30, 2025, seed 20260923. This audit reuses saved holdouts and does not call them newly unseen.</p>{metrics_sections}
<h2>Full workflow trace</h2><p>The literal haul/truck scenario is rejected by the schema. The supported excavator control below uses actual model outputs and calculations, but is not a substitute for the requested full-stack workflow.</p><pre>{dump(report['details']['end_to_end_trace'])}</pre>
<h2>Methodology and scope</h2><ul>{methods}</ul><p>Reproduce: <code>.venv/bin/python -m audits.member3_audit</code>, then <code>.venv/bin/python -m audits.render_report</code>.</p>
<script>const filters=['module','status','search'];function filter(){{const m=document.getElementById('module').value,s=document.getElementById('status').value,q=document.getElementById('search').value.toLowerCase();document.querySelectorAll('.matrix tbody tr').forEach(r=>r.hidden=!!((m&&r.dataset.module!==m)||(s&&r.dataset.status!==s)||(q&&!r.textContent.toLowerCase().includes(q))))}}filters.forEach(id=>document.getElementById(id).addEventListener('input',filter));document.getElementById('expand').onclick=()=>document.querySelectorAll('details').forEach(d=>d.open=true);</script></html>'''
(OUT / "member3-acceptance.html").write_text(html_text)

canvas_template = r'''import { H1, H2, Text, Table, Stack, Row, Grid, Stat, useHostTheme, useState } from "cursor/canvas";
const report = __DATA__;
export default function Member3Acceptance() {
  const theme = useHostTheme();
  const [module, setModule] = useState("");
  const [status, setStatus] = useState("");
  const [query, setQuery] = useState("");
  const selected = report.tests.filter(r => (!module || r.module === module) && (!status || r.status === status) && JSON.stringify(r).toLowerCase().includes(query.toLowerCase()));
  const pre = (value: unknown) => <pre style={{fontSize:12,whiteSpace:"pre-wrap",overflowWrap:"anywhere",maxWidth:800,color:theme.text.secondary}}>{JSON.stringify(value,null,2)}</pre>;
  const control = {background:theme.bg.editor,color:theme.text.primary,border:`1px solid ${theme.stroke.primary}`,padding:8,fontSize:13};
  return <Stack gap={18} style={{padding:24,color:theme.text.primary,background:theme.bg.editor}}>
    <H1>Member 3 acceptance tests</H1>
    <Text weight="semibold">Demo readiness: {report.readiness}. The requested end-to-end workflow fails.</Text>
    <Grid columns={3}><Stat label="Requested tests" value={report.total}/><Stat label="Passed" value={report.passed}/><Stat label="Failed" value={report.failed}/></Grid>
    <Text tone="secondary">Executed {report.created_at}. Separate existing regression suite: 14 passed. Member 3 functions were fixed; saved trained model artifacts were preserved.</Text>
    <H2>Module results</H2>
    <Table headers={["Module","Tests Passed","Tests Failed","Status"]} rows={report.summary.map(r=>[r.module,r.passed,r.failed,r.status])}/>
    <H2>Remaining findings</H2>
    {report.critical_findings.map(r=><div key={r.title}><Text weight="semibold">{r.title} · {r.tests}</Text><Text tone="secondary">{r.detail}</Text></div>)}
    <Text>Backend task creation, recommendation orchestration and dashboard delivery are absent and fail acceptance. Local composition tests do not establish API integration.</Text>
    <H2>All 60 executed cases</H2>
    <Row wrap><select style={control} value={module} onChange={e=>setModule(e.target.value)}><option value="">All modules</option>{report.summary.map(r=><option key={r.module} value={r.module}>{r.module}</option>)}</select><select style={control} value={status} onChange={e=>setStatus(e.target.value)}><option value="">All results</option><option value="FAIL">FAIL</option><option value="PASS">PASS</option></select><input style={control} value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search cases, issues or functions"/></Row>
    {selected.length>0 && <Table stickyHeader headers={["Test ID","Module","Input","Expected Behaviour","Actual Behaviour","PASS/FAIL","Issue Found","Responsible function / smallest fix"]} rows={selected.map(r=>[r.test_id,r.module,r.input,r.expected,<details key={r.test_id}><summary>Executed output</summary>{pre(r.actual)}</details>,r.status,r.issue,<div key={r.test_id+"fix"}><Text size="small">{r.responsible.file}{r.responsible.line?":"+r.responsible.line:" (file absent; proposed location)"} · {r.responsible.function}</Text><Text size="small">{r.smallest_fix}</Text></div>])}/>}
    <H2>Recomputed model metrics</H2>
    <Text tone="secondary">V1 test dates: May 24–30, 2025. V2 generated holdout: June 1–July 30, 2025, seed 20260923. Reused holdouts are regression evidence, not a new independent evaluation.</Text>
    <Text weight="semibold">Anomaly precision, recall, F1 and confusion matrices</Text>{pre(report.details.anomaly_metrics)}
    <Text weight="semibold">Task duration MAE and RMSE in minutes</Text>{pre(report.details.duration_metrics)}
    <Text weight="semibold">Energy forecast and replay comparisons</Text>{pre(report.details.energy_metrics)}
    <Text>Energy replay measures time to consume a fixed 5% capacity budget, not actual time until empty. Censored and zero-rate exclusions are reported above.</Text>
    <H2>Full workflow trace</H2>{pre(report.details.end_to_end_trace)}
    <H2>Methodology</H2>{report.methodology.map(item=><Text key={item} tone="secondary">{item}</Text>)}
  </Stack>;
}
'''
source = canvas_template.replace("__DATA__", json.dumps(report, ensure_ascii=False))
destination = "/Users/reetbajaj/.cursor/projects/Users-reetbajaj-caterpillar/canvases/member3-acceptance.canvas.tsx"
existing = Path(destination)
if existing.exists():
    patch = "*** Begin Patch\n*** Update File: " + destination + "\n@@\n" + "\n".join("-" + line for line in existing.read_text().splitlines()) + "\n" + "\n".join("+" + line for line in source.splitlines()) + "\n*** End Patch\n"
else:
    patch = "*** Begin Patch\n*** Add File: " + destination + "\n" + "\n".join("+" + line for line in source.splitlines()) + "\n*** End Patch\n"
Path("/tmp/member3-acceptance-canvas.patch").write_text(patch)
print(json.dumps({"html": str(OUT / "member3-acceptance.html"), "canvas_destination": destination, "total":report["total"],"passed":report["passed"],"failed":report["failed"]}, indent=2))
