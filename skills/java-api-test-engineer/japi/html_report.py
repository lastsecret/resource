"""Static, escaped HTML representation of a machine-readable diff artifact."""
from __future__ import annotations
from html import escape
import json
from pathlib import Path


def render_diff(data,path):
    summary=data['summary']
    rows=[]
    for c in data['cases']:
        differences=escape(json.dumps(c.get('differences',[]),ensure_ascii=False,indent=2))
        warnings=escape(json.dumps(c.get('quality_warnings',[]),ensure_ascii=False,indent=2))
        outcome=escape(c['outcome'])
        rows.append(f'<tr><td>{escape(str(c.get("case_id","")))}</td>'
          f'<td>{escape(str(c.get("endpoint_id","")))}</td>'
          f'<td class="{outcome}">{outcome}</td>'
          f'<td>{escape(str(c.get("quality_confidence","unknown")))}</td>'
          f'<td><details><summary>{len(c.get("differences",[]))} differences</summary><pre>{differences}</pre></details></td>'
          f'<td><details><summary>{len(c.get("quality_warnings",[]))} warnings</summary><pre>{warnings}</pre></details></td></tr>')
    page='''<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>JAPI A/B Regression Report</title><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{font:14px/1.55 system-ui,sans-serif;max-width:1300px;margin:32px auto;padding:0 18px;color:#20242b}
header{border-bottom:1px solid #ddd;margin-bottom:20px}h1{font-size:25px}table{width:100%;border-collapse:collapse}
th,td{padding:11px;border-bottom:1px solid #dedfe2;text-align:left;vertical-align:top;overflow-wrap:anywhere}
th{background:#f5f6f8}td.same{color:#116a3d;font-weight:bold}td.different{color:#a12424;font-weight:bold}
td.inconclusive{color:#ad6b00;font-weight:bold}pre{white-space:pre-wrap;overflow-wrap:anywhere;font:12px ui-monospace,monospace}
.summary{font-size:16px;color:#555}summary{cursor:pointer}p.small{color:#67707f;font-size:12px}</style></head><body>
<header><h1>Java API A/B Regression Report</h1><p class="summary">'''+escape(' · '.join(f'{key}: {value}' for key,value in summary.items()))+'''</p></header>
<p class="small">Comparison policy is retained in diff.json. A passing response comparison is not proof of adequate test data coverage.</p>
<table><thead><tr><th>Case</th><th>Endpoint</th><th>Outcome</th><th>Confidence</th><th>Differences</th><th>Case warnings</th></tr></thead><tbody>'''+''.join(rows)+'''</tbody></table></body></html>'''
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(page,encoding='utf-8')
