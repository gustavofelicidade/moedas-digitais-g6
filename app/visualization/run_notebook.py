"""CLI runner to execute any Jupyter notebook (.ipynb) in-place and optionally export to standalone HTML with embedded tables and plots, without requiring jupyter/nbconvert."""

from __future__ import annotations

import argparse
import base64
import html
import io
import json
from pathlib import Path
import sys
import traceback

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def execute_notebook(nb_path: Path, html_out: Path | None = None) -> None:
    nb = json.loads(nb_path.read_text(encoding="utf-8"))
    env: dict = {"__name__": "__main__"}
    exec_count = 1
    html_sections: list[str] = []

    for idx, cell in enumerate(nb.get("cells", [])):
        ctype = cell.get("cell_type")
        source_text = "".join(cell.get("source", []))
        if ctype == "markdown":
            html_sections.append(f"<div class='md-cell'><pre class='md-raw'>{html.escape(source_text)}</pre></div>")
            continue
        if ctype != "code":
            continue

        outputs = []
        stdout_buf = io.StringIO()

        def custom_display(obj):
            if isinstance(obj, pd.DataFrame):
                outputs.append({
                    "output_type": "execute_result",
                    "execution_count": exec_count,
                    "data": {
                        "text/plain": obj.to_string(),
                        "text/html": obj.to_html(index=False, classes="dataframe"),
                    },
                    "metadata": {},
                })
            else:
                outputs.append({
                    "output_type": "display_data",
                    "data": {"text/plain": repr(obj)},
                    "metadata": {},
                })

        def custom_show(*_args, **_kwargs):
            for fig_num in plt.get_fignums():
                fig = plt.figure(fig_num)
                img_buf = io.BytesIO()
                fig.savefig(img_buf, format="png", dpi=135, bbox_inches="tight")
                img_b64 = base64.b64encode(img_buf.getvalue()).decode("ascii")
                outputs.append({
                    "output_type": "display_data",
                    "data": {
                        "image/png": img_b64,
                        "text/plain": "<Figure>",
                    },
                    "metadata": {},
                })
            plt.close("all")

        env["display"] = custom_display
        plt.show = custom_show

        old_stdout = sys.stdout
        sys.stdout = stdout_buf
        try:
            exec(compile(source_text, f"{nb_path.name}#cell_{idx}", "exec"), env)
        except Exception as exc:
            sys.stdout = old_stdout
            print(f"[ERRO] Falha na célula {idx}: {exc}")
            traceback.print_exc()
            raise
        finally:
            sys.stdout = old_stdout

        printed = stdout_buf.getvalue()
        if printed:
            outputs.insert(0, {
                "output_type": "stream",
                "name": "stdout",
                "text": [line + "\n" for line in printed.splitlines()],
            })

        cell["execution_count"] = exec_count
        cell["outputs"] = outputs
        print(f"[OK] Célula de código [{exec_count}] executada ({len(outputs)} saída(s))")

        cell_html = [f"<div class='code-cell'><div class='code-header'>In [{exec_count}]:</div><pre class='code-input'>{html.escape(source_text)}</pre>"]
        for out in outputs:
            otype = out.get("output_type")
            if otype == "stream":
                txt = "".join(out.get("text", []))
                cell_html.append(f"<pre class='stream-out'>{html.escape(txt)}</pre>")
            elif otype in ("execute_result", "display_data"):
                data = out.get("data", {})
                if "text/html" in data:
                    cell_html.append(f"<div class='table-out'>{data['text/html']}</div>")
                elif "image/png" in data:
                    cell_html.append(f"<div class='img-out'><img src='data:image/png;base64,{data['image/png']}' /></div>")
                elif "text/plain" in data:
                    cell_html.append(f"<pre class='plain-out'>{html.escape(str(data['text/plain']))}</pre>")
        cell_html.append("</div>")
        html_sections.append("\n".join(cell_html))
        exec_count += 1

    nb_path.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[SUCESSO] Notebook atualizado in-place: {nb_path}")

    if html_out is not None:
        html_doc = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>{html.escape(nb_path.stem)} — Relatório Consolidado OONCA</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 1180px; margin: 24px auto; padding: 0 20px; background: #f8f9fa; color: #212529; }}
  .md-cell {{ background: #ffffff; border-left: 4px solid #2a9d8f; padding: 14px 18px; margin: 18px 0; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.06); }}
  .md-raw {{ white-space: pre-wrap; font-family: inherit; margin: 0; line-height: 1.5; }}
  .code-cell {{ background: #ffffff; border: 1px solid #dee2e6; border-radius: 6px; margin: 18px 0; padding: 14px 18px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }}
  .code-header {{ font-weight: bold; color: #264653; font-family: monospace; margin-bottom: 6px; }}
  .code-input {{ background: #f1f3f5; padding: 10px; border-radius: 4px; overflow-x: auto; font-size: 12.5px; }}
  .stream-out {{ background: #1d3557; color: #f1faee; padding: 10px 12px; border-radius: 4px; overflow-x: auto; font-size: 12.5px; }}
  .table-out {{ overflow-x: auto; margin: 12px 0; }}
  table.dataframe {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
  table.dataframe th, table.dataframe td {{ border: 1px solid #dee2e6; padding: 7px 10px; text-align: left; }}
  table.dataframe th {{ background: #264653; color: #ffffff; }}
  table.dataframe tr:nth-child(even) {{ background: #f8f9fa; }}
  .img-out img {{ max-width: 100%; height: auto; border: 1px solid #e9ecef; border-radius: 4px; margin-top: 10px; }}
</style>
</head>
<body>
<h1>Relatório Executado via CLI: {html.escape(nb_path.name)}</h1>
{"".join(html_sections)}
</body>
</html>"""
        html_out.parent.mkdir(parents=True, exist_ok=True)
        html_out.write_text(html_doc, encoding="utf-8")
        print(f"[SUCESSO] Relatório HTML salvo em: {html_out}")


def main():
    parser = argparse.ArgumentParser(description="Executa um notebook (.ipynb) in-place via CLI e opcionalmente exporta HTML")
    parser.add_argument("notebook", nargs="?", default="notebooks/entregavel_datathon_fgv.ipynb", help="Caminho do arquivo .ipynb")
    parser.add_argument("--html", help="Caminho opcional para exportar relatório HTML completo")
    args = parser.parse_args()
    nb_path = Path(args.notebook).resolve()
    html_path = Path(args.html).resolve() if args.html else nb_path.with_suffix(".html")
    execute_notebook(nb_path, html_path)


if __name__ == "__main__":
    main()
