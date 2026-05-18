BASE_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='8' fill='%230f172a'/%3E%3Ctext x='16' y='22' text-anchor='middle' font-family='system-ui' font-size='16' font-weight='bold' fill='white'%3EH%3C/text%3E%3C/svg%3E">
    <script nonce="{{ nonce }}">
        (() => {
            try {
                const saved = localStorage.getItem('aihistory-theme');
                const mode = saved || 'light';
                if (mode === 'dark') document.documentElement.classList.add('dark');
            } catch (_) {}
        })();
    </script>
    <script src="/static/tailwind-3.4.16.min.js"></script>
    <link rel="stylesheet" href="/static/highlight-github-11.9.0.min.css">
    <script nonce="{{ nonce }}">
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        bg: "#09090b",
                        surface: "#121214",
                        border: "#1f1f23",
                        accent: "#3b82f6",
                    }
                }
            }
        }
    </script>
    <style nonce="{{ nonce }}">
        :root {
            --bg: #f6f7fb;
            --text: #0f172a;
            --panel: rgba(255, 255, 255, 0.86);
            --panel-strong: #ffffff;
            --border: #dbe2ea;
            --muted: #64748b;
            --card: #ffffff;
            --main: rgba(247, 250, 255, 0.72);
        }
        html.dark {
            --bg: #090b12;
            --text: #e2e8f0;
            --panel: rgba(15, 23, 42, 0.72);
            --panel-strong: #0f172a;
            --border: #253247;
            --muted: #94a3b8;
            --card: #0f172a;
            --main: rgba(5, 9, 20, 0.68);
        }
        body { background-color: var(--bg); color: var(--text); font-family: "Helvetica Neue", Inter, Arial, ui-sans-serif, -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif; position: relative; }
        .skip-link { position: absolute; left: 8px; top: -48px; z-index: 200; background: #0f172a; color: #ffffff; padding: 10px 16px; border-radius: 8px; font-size: 13px; font-weight: 600; text-decoration: none; transition: top 0.15s ease; }
        .skip-link:focus { top: 8px; outline: 2px solid #3b82f6; outline-offset: 2px; }
        body.session-view { background: #f8fafc; }
        body::before { content:""; position: fixed; inset: 0; background:
            radial-gradient(circle at 18% 8%, rgba(147, 197, 253, 0.28), transparent 42%),
            radial-gradient(circle at 82% 0%, rgba(244, 114, 182, 0.12), transparent 38%),
            radial-gradient(circle at 10% 82%, rgba(34, 197, 94, 0.13), transparent 46%);
            z-index: -1;
        }
        body.session-view::before { display: none; }
        html.dark body::before { background:
            radial-gradient(circle at 20% 10%, rgba(59, 130, 246, 0.25), transparent 44%),
            radial-gradient(circle at 85% 0%, rgba(168, 85, 247, 0.14), transparent 42%),
            radial-gradient(circle at 8% 85%, rgba(20, 184, 166, 0.14), transparent 48%);
        }
        .title-font { font-family: "Helvetica Neue", Inter, Arial, ui-sans-serif, -apple-system, BlinkMacSystemFont, "SF Pro Text", sans-serif; letter-spacing: -0.015em; }
        .mono-ui, code, pre, kbd, .code-card-meta, .message-time, .toc-item-meta { font-family: "Source Code Pro", "SF Mono", Menlo, monospace; }
        .prose { font-size: 14px; line-height: 1.75; color: var(--text); }
        .prose p { margin-bottom: 1.15em; }
        .prose pre { background: #f8fafc !important; border: 1px solid #e2e8f0; border-radius: 14px; margin: 1.5em 0; overflow-x: auto; max-width: 100%; }
        html.dark .prose pre { background: #0b1220 !important; border-color: #273449; }
        .prose pre.collapsed { max-height: 400px; overflow-y: hidden; position: relative; }
        .prose pre.collapsed::after { content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 80px; background: linear-gradient(to bottom, transparent, #f8fafc); pointer-events: none; }
        html.dark .prose pre.collapsed::after { background: linear-gradient(to bottom, transparent, #0b1220); }
        .prose code { font-family: "SF Mono", Menlo, monospace; font-size: 12.5px; background: #eef2ff; padding: 2px 4px; border-radius: 4px; word-break: break-all; white-space: pre-wrap; }
        html.dark .prose code { background: #1e293b; color: #e2e8f0; }
        .prose pre code { background: transparent; padding: 0; white-space: pre; word-break: normal; display: block; }
        .message-card { border-radius: 14px; border: 1px solid var(--border); background: var(--card); box-shadow: none; }
        .message-user { background: #eef6ff; border-color: #bfdbfe; color: #0f172a; }
        .message-user .prose { color: #0f172a; }
        .message-user .prose code { background: #dbeafe; color: #1e3a8a; }
        .message-user .prose pre { background: #eff6ff !important; border-color: #bfdbfe; }
        .message-user .prose a { color: #2563eb; }
        html.dark .message-user { background: #0f223b; border-color: #2f4d76; color: #dbeafe; }
        html.dark .message-user .prose { color: #dbeafe; }
        html.dark .message-user .prose code { background: #1d3557; color: #dbeafe; }
        .message-agent { border-left: 3px solid rgba(59, 130, 246, 0.35); background: var(--panel-strong); }
        .pill { padding: 2px 10px; border-radius: 999px; font-size: 10px; letter-spacing: 0.16em; font-weight: 600; text-transform: uppercase; }
        .toc-card { background: #ffffff; border: 1px solid #e5e7eb; border-radius: 14px; display: flex; flex-direction: column; overflow: hidden; box-shadow: 0 1px 2px rgba(2, 8, 23, 0.04); }
        .toc-card-head { padding: 12px 14px; border-bottom: 1px solid #f1f5f9; font-size: 12px; font-weight: 700; color: #334155; letter-spacing: 0.01em; }
        .toc-list { padding: 8px; overflow-y: auto; scroll-behavior: smooth; scrollbar-width: thin; scrollbar-color: #cbd5e1 transparent; }
        .toc-list::-webkit-scrollbar { width: 4px; }
        .toc-list::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
        .toc-list::-webkit-scrollbar-track { background: transparent; }
        .toc-item { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; align-items: center; gap: 8px; width: 100%; padding: 6px 10px; border-radius: 8px; color: #0f172a; border: 1px solid transparent; transition: all 0.15s ease; text-decoration: none; }
        .toc-item-text { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; letter-spacing: -0.01em; color: #334155; }
        .toc-item-meta { font-size: 11px; font-family: "SF Mono", Menlo, monospace; color: #5b6573; }
        .toc-item:hover { background: #f8fafc; color: #0f172a; border-color: #f1f5f9; }
        html.dark .toc-item:hover { background: #182133; color: #e2e8f0; }
        .toc-item.active { background: #eff6ff; color: #0f172a; border-color: #dbeafe; }
        html.dark .toc-item.active { background: #1e293b; color: #e2e8f0; }
        .toc-badge { width: 22px; height: 22px; border-radius: 999px; display: inline-flex; align-items: center; justify-content: center; font-size: 12px; border: 1px solid #e2e8f0; color: #64748b; background: #ffffff; font-weight: 600; }
        html.dark .toc-badge { background: #0f172a; border-color: #334155; color: #cbd5e1; }
        .toc-item.active .toc-badge { background: #3b82f6; color: #ffffff; border-color: #3b82f6; }
        .toc-stepper { position: relative; }
        .toc-stepper::before { content: ""; position: absolute; left: 21px; top: 12px; bottom: 12px; width: 1px; background: #e2e8f0; }
        html.dark .toc-stepper::before { background: #334155; }
        .code-card { border: 1px solid #e2e8f0; border-radius: 16px; overflow: hidden; background: #ffffff; }
        html.dark .code-card { border-color: #334155; background: #0f172a; }
        .code-card-header { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 8px 12px; background: #f8fafc; border-bottom: 1px solid #e2e8f0; font-size: 11px; color: #64748b; }
        html.dark .code-card-header { background: #111827; border-color: #334155; color: #94a3b8; }
        .code-card-title { font-weight: 600; color: #0f172a; }
        html.dark .code-card-title { color: #e2e8f0; }
        .code-card-meta { font-family: "SF Mono", Menlo, monospace; }
        .prompt-row { display: flex; align-items: center; gap: 8px; font-size: 10px; text-transform: uppercase; letter-spacing: 0.18em; color: #94a3b8; }
        .prompt-pill { padding: 2px 8px; border-radius: 999px; border: 1px solid #e2e8f0; background: #ffffff; font-weight: 600; letter-spacing: 0.12em; color: #64748b; }
        .prompt-icon { min-width: 34px; height: 22px; padding: 0 8px; border-radius: 8px; display: inline-flex; align-items: center; justify-content: center; background: var(--primary); color: #ffffff; font-size: 10px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; }
        .response-icon { min-width: 34px; height: 22px; padding: 0 8px; border-radius: 8px; display: inline-flex; align-items: center; justify-content: center; border: 1px solid var(--assistant-border); font-size: 10px; font-weight: 700; letter-spacing: 0.06em; text-transform: uppercase; background: var(--assistant-bg); color: var(--assistant-text); }
        pre.diff-block { border: 1px solid #e2e8f0; background: #f8fafc; box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.15); }
        pre.diff-block code { font-size: 12px; }
        pre.diff-block .hljs-addition { background: rgba(34, 197, 94, 0.12); color: #166534; display: block; }
        pre.diff-block .hljs-deletion { background: rgba(239, 68, 68, 0.12); color: #7f1d1d; display: block; }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 10px; }
        .sidebar-link { display:flex; align-items:center; padding:0.5rem 0.75rem; border-radius:0.75rem; font-size:0.875rem; color:var(--muted); transition: all 0.2s ease; }
        .sidebar-link:hover { color:#0f172a; background:#f1f5f9; }
        html.dark .sidebar-link:hover { color:#f1f5f9; background:#1f2937; }
        .sidebar-link.active { background:#ffffff; color:#0f172a; border:1px solid #e5e7eb; box-shadow: 0 16px 30px -35px rgba(15, 23, 42, 0.4); }
        html.dark .sidebar-link.active { background:#111827; color:#f8fafc; border-color:#334155; }
        .app-panel { background: var(--panel); border-color: var(--border) !important; }
        .app-main { background: var(--main); }
        .theme-toggle { border-color: var(--border) !important; background: var(--panel-strong) !important; color: var(--muted) !important; }
        .surface-card { background: var(--card); border: 1px solid var(--border); border-radius: 16px; box-shadow: 0 10px 30px -28px rgba(2, 8, 23, 0.5); }
        body.session-view .surface-card { background: #ffffff; border-color: #e5e7eb; box-shadow: 0 1px 2px rgba(2, 8, 23, 0.04); }
        .stat-card { background: linear-gradient(135deg, var(--card), color-mix(in srgb, var(--card) 82%, #dbeafe 18%)); border: 1px solid var(--border); border-radius: 16px; }
        .list-row { border: 1px solid var(--border); background: var(--card); border-radius: 16px; transition: transform 0.15s ease, box-shadow 0.2s ease, border-color 0.2s ease; }
        .list-row:hover { transform: translateY(-1px); box-shadow: 0 14px 26px -22px rgba(15, 23, 42, 0.55); border-color: color-mix(in srgb, var(--border) 65%, #60a5fa 35%); }
        .tag-chip { padding: 3px 10px; border-radius: 999px; border: 1px solid var(--border); font-size: 10px; letter-spacing: 0.02em; color: var(--muted); background: color-mix(in srgb, var(--card) 88%, #e2e8f0 12%); }
        .section-title { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.2em; color: var(--muted); }
        .page-headline { font-size: 30px; line-height: 1.05; letter-spacing: -0.025em; }
        .meta-line { font-size: 12px; color: var(--muted); }
        .compact-list { display: flex; flex-direction: column; gap: 8px; }
        .compact-row { border: 1px solid var(--border); background: var(--card); border-radius: 14px; padding: 12px; transition: transform 0.15s ease, border-color 0.2s ease, box-shadow 0.2s ease; }
        .compact-row:hover { transform: translateY(-1px); border-color: color-mix(in srgb, var(--border) 65%, #60a5fa 35%); box-shadow: 0 12px 22px -20px rgba(2, 8, 23, 0.45); }
        .compact-title { font-size: 15px; font-weight: 650; letter-spacing: -0.01em; line-height: 1.25; }
        .message-cluster { border: 1px solid #e5e7eb; background: #ffffff; border-radius: 14px; padding: 14px; }
        body.session-view .message-cluster { border-color: #e2e8f0; border-radius: 12px; padding: 12px; }
        .message-time { font-size: 10px; color: #5b6573; font-family: "SF Mono", Menlo, monospace; }
        .turn-row { display: flex; gap: 14px; align-items: flex-start; }
        .turn-row.user { justify-content: flex-end; }
        .turn-row.assistant { justify-content: flex-start; }
        .turn-gutter { width: 32px; flex-shrink: 0; display: flex; justify-content: center; }
        .turn-index { width: 22px; height: 22px; border-radius: 999px; display: inline-flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; border: 1px solid var(--border); background: var(--panel-strong); color: var(--muted); }
        .turn-index.user { background: #dbeafe; color: #1e3a8a; border-color: #93c5fd; }
        .turn-index.assistant { background: #ecfeff; color: #155e75; border-color: #67e8f9; }
        .turn-content { flex: 1; min-width: 0; max-width: 100%; }
        .turn-content.user-content { max-width: 920px; }
        .turn-content.assistant-content { max-width: 100%; }
        body.session-view .turn-row { gap: 8px; }
        body.session-view .turn-gutter { width: 0; display: none; }
        .role-badge { display: inline-flex; align-items: center; gap: 6px; font-size: 10px; text-transform: uppercase; letter-spacing: 0.16em; font-weight: 700; color: var(--muted); }
        .role-dot { width: 7px; height: 7px; border-radius: 999px; display: inline-block; }
        .role-dot.user { background: #2563eb; }
        .role-dot.assistant { background: #06b6d4; }
        .message-card.user-card { border: 1px solid #dbeafe; background: #f5f9ff; color: #0f172a; box-shadow: none; }
        .message-card.user-card .prose { color: #0f172a; }
        .message-card.user-card .prose code { background: #bfdbfe; color: #1e3a8a; }
        html.dark .message-card.user-card { background: #102946; border-color: #2f5a87; color: #dbeafe; }
        html.dark .message-card.user-card .prose { color: #dbeafe; }
        .message-card.assistant-card { border: 1px solid #e5e7eb; background: #ffffff; }
        body.session-view .message-card.user-card,
        body.session-view .message-card.assistant-card { border-radius: 12px; }
        html.dark .message-card.assistant-card { background: color-mix(in srgb, var(--card) 98%, #0b1220 2%); }
        .tool-chip { display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 999px; border: 1px solid #e2e8f0; background: #f8fafc; font-size: 11px; font-weight: 600; color: #475569; }
        .thinking-summary { display: inline-flex; align-items: center; gap: 6px; font-size: 11px; font-weight: 600; letter-spacing: 0.02em; color: #6366f1; }
        .thinking-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.12em; color: #818cf8; background: #eef2ff; padding: 2px 8px; border-radius: 999px; }
        html.dark .thinking-label { background: #1e1b4b; color: #a5b4fc; }
        html.dark .thinking-summary { color: #a5b4fc; }
        .thinking-content { background: #fafafe; border: 1px solid #e0e7ff; border-radius: 10px; padding: 14px 16px; font-size: 13px; line-height: 1.65; color: #475569; white-space: pre-wrap; word-break: break-word; max-height: 400px; overflow-y: auto; }
        html.dark .thinking-content { background: #0f0e24; border-color: #312e81; color: #c7d2fe; }
        .assistant-stream { display: flex; flex-direction: column; gap: 12px; margin-top: 10px; margin-left: 0; padding-left: 0; }
        .assistant-entry { border-top: none; padding-top: 0; }
        .assistant-entry:first-child { border-top: none; padding-top: 0; }
        body.session-view .assistant-stream { border-left: none; margin-left: 0; padding-left: 0; gap: 12px; margin-top: 10px; }
        body.session-view .assistant-entry { border-top-color: #e2e8f0; padding-top: 12px; }
        .action-block { border: none; border-radius: 0; background: transparent; margin: 8px 0; overflow: visible; }
        .action-block summary { list-style: none; cursor: pointer; padding: 7px 12px; display: inline-flex; align-items: center; gap: 7px; font-size: 12px; color: #475569; border: 1px solid #e5e7eb; border-radius: 10px; background: #ffffff; max-width: 100%; transition: all 0.15s ease; }
        .action-block summary::-webkit-details-marker { display: none; }
        .action-block summary:hover { background: #f8fafc; border-color: #dbe2ea; }
        .action-block[open] summary { border-bottom-left-radius: 0; border-bottom-right-radius: 0; border-bottom-color: transparent; margin-bottom: -1px; position: relative; z-index: 1; }
        .action-block .action-content { border: 1px solid #e5e7eb; border-top: none; border-radius: 0 0 10px 10px; background: #ffffff; padding: 12px; animation: slideDown 0.15s ease-out; }
        @keyframes slideDown { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }
        .tool-call-pill { min-height: 32px; display: inline-flex; align-items: center; gap: 7px; width: fit-content; border: 1px solid #e5e7eb; border-radius: 10px; background: #ffffff; padding: 7px 12px; font-size: 12px; font-weight: 500; color: #1f2937; transition: all 0.15s ease; }
        .tool-call-pill:hover { background: #f8fafc; border-color: #dbe2ea; }
        .tool-result-pill.status-error { border-color: #fecaca; background: #fef2f2; }
        .tool-result-pill.status-ok { border-color: #bbf7d0; background: #f0fdf4; }
        .tool-call-icon { opacity: 0.85; }
        .action-meta-group { display: inline-flex; align-items: center; gap: 6px; }
        .action-chevron { width: 14px; transition: transform 0.2s ease; opacity: 0.6; }
        details[open] .action-chevron { transform: rotate(90deg); }
        .action-title { font-weight: 600; color: #334155; }
        .action-meta { font-size: 10px; letter-spacing: 0.06em; text-transform: uppercase; color: #94a3b8; font-family: "Source Code Pro", "SF Mono", Menlo, monospace; }
        .action-content { font-size: 12px; display: flex; flex-direction: column; gap: 10px; }
        .action-section-title { font-size: 10px; text-transform: uppercase; letter-spacing: 0.14em; color: #94a3b8; font-weight: 700; margin-top: 2px; }
        .action-kv-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 8px; }
        .action-kv-item { border: 1px solid var(--border); border-radius: 10px; background: color-mix(in srgb, var(--card) 96%, #f8fafc 4%); padding: 8px; }
        .action-kv-key { font-size: 10px; text-transform: uppercase; letter-spacing: 0.12em; color: #94a3b8; margin-bottom: 4px; }
        .action-kv-value { font-size: 12.5px; color: #334155; line-height: 1.5; word-break: break-word; }
        .action-code, .action-output { margin: 0; border: 1px solid #e5e7eb; border-radius: 10px; background: #f8fafc; overflow: auto; }
        .action-code code, .action-output code { display: block; padding: 14px 16px; font-size: 13px; line-height: 1.6; font-family: "Source Code Pro", "SF Mono", Menlo, monospace; }
        .action-code code { white-space: pre-wrap; word-break: break-word; overflow-wrap: anywhere; }
        .action-output code { white-space: pre; }
        body.session-view .prose pre { border-radius: 10px; border-color: #e2e8f0; background: #f8fafc !important; margin: 1.1em 0; }
        body.session-view .prose pre code { padding: 14px 16px; font-size: 13px; line-height: 1.58; }
        body.session-view .prose code { background: #f1f5f9; word-break: break-word; white-space: normal; }
        body.session-view .cmd-tag { background: #fef3c7; color: #92400e; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }
        body.session-view .cmd-name { background: #dbeafe; color: #1e3a8a; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; font-weight: 600; }
        body.session-view .cmd-args { background: #f3f4f6; color: #374151; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }
        html.dark body.session-view .cmd-tag { background: #78350f; color: #fef3c7; }
        html.dark body.session-view .cmd-name { background: #1e3a8a; color: #dbeafe; }
        html.dark body.session-view .cmd-args { background: #374151; color: #e5e7eb; }
        body.session-view .role-badge { font-size: 10px; letter-spacing: 0.1em; color: #64748b; }
        body.session-view .role-dot { width: 6px; height: 6px; }
        body.session-view .tool-chip { font-size: 10px; padding: 2px 8px; }
        body.session-view .message-time { opacity: 0.8; }
        body.session-view .turn-content.user-content .message-card { max-width: 95%; }
        html.dark .tool-call-pill { border-color: #334155; background: #0f172a; color: #cbd5e1; }
        html.dark .tool-call-pill:hover { background: #111827; border-color: #475569; }
        .action-raw summary { font-size: 10px; letter-spacing: 0.12em; text-transform: uppercase; color: #94a3b8; cursor: pointer; }
        .tool-chip.status-ok { border-color: #86efac; color: #166534; background: #f0fdf4; }
        .tool-chip.status-error { border-color: #fca5a5; color: #991b1b; background: #fef2f2; }
        .tool-chip.status-neutral { border-color: #cbd5e1; color: #334155; background: #f8fafc; }
        html.dark .toc-card { background: #0f172a; border-color: #334155; }
        html.dark .toc-card-head { border-bottom-color: #1e293b; color: #cbd5e1; }
        html.dark .toc-item-text { color: #cbd5e1; }
        html.dark .action-block summary { background: #0f172a; border-color: #334155; color: #cbd5e1; }
        html.dark .action-title { color: #cbd5e1; }
        html.dark .action-kv-item { background: color-mix(in srgb, var(--card) 96%, #0b1220 4%); }
        html.dark .action-kv-value { color: #cbd5e1; }
        html.dark .action-code, html.dark .action-output { background: #0b1220; border-color: #334155; }
        .session-headline { font-size: 17px; line-height: 1.35; letter-spacing: -0.012em; font-weight: 600; color: var(--text); }
        .session-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; font-size: 12px; color: var(--text-muted); }
        .session-meta-dot { width: 4px; height: 4px; border-radius: 999px; background: #cbd5e1; display: inline-block; }
        .toc-card-foot { padding: 10px 14px; border-top: 1px solid #f1f5f9; font-size: 12px; color: #64748b; font-family: "Source Code Pro", "SF Mono", Menlo, monospace; }
        html.dark .toc-card-foot { border-top-color: #1e293b; color: #94a3b8; }
        html.dark .tool-chip.status-ok { border-color: #16a34a66; color: #86efac; background: #052e16; }
        html.dark .tool-chip.status-error { border-color: #dc262666; color: #fca5a5; background: #450a0a; }
        html.dark .tool-chip.status-neutral { border-color: #334155; color: #cbd5e1; background: #0f172a; }
        .top-controls { display: inline-flex; align-items: center; gap: 8px; }
        .density-toggle, .clean-toggle, .readability-toggle, .ultra-clean-toggle, .presenter-toggle, .cancel-toggle { border-color: var(--border) !important; background: var(--panel-strong) !important; color: var(--muted) !important; font-size: 11px; padding: 0 10px; height: 34px; border-radius: 999px; }
        .reload-group { display: inline-flex; align-items: center; border: 1px solid var(--border); border-radius: 999px; overflow: hidden; background: var(--panel-strong); }
        .reload-group select { border: none !important; border-right: 1px solid var(--border) !important; border-radius: 0 !important; height: 34px; background: transparent !important; min-width: 128px; }
        .reload-group button { border: none !important; border-radius: 0 !important; height: 34px; min-width: 82px; background: transparent !important; }
        .reload-group select:focus, .reload-group button:focus { outline: none; }
        .view-menu { position: relative; }
        .view-menu > summary { list-style: none; cursor: pointer; }
        .view-menu > summary::-webkit-details-marker { display: none; }
        .view-menu-panel { position: absolute; right: 0; top: calc(100% + 8px); min-width: 220px; background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; box-shadow: 0 10px 26px -18px rgba(2, 8, 23, 0.45); padding: 10px; display: none; z-index: 50; }
        .view-menu[open] .view-menu-panel { display: block; }
        .view-menu-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
        .view-menu-grid button { width: 100%; justify-content: center; }
        .view-menu-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.12em; color: #94a3b8; margin-bottom: 8px; font-weight: 700; }
        body.session-view .app-main > .h-16 { height: 58px; background: #ffffffcc; }
        html.dark .view-menu-panel { background: #0f172a; border-color: #334155; }
        .search-modal { display: none; visibility: hidden; opacity: 0; pointer-events: none; transition: opacity 0.15s ease; }
        .search-modal.open { display: flex; visibility: visible; opacity: 1; pointer-events: auto; }
        .density-toggle.active, .clean-toggle.active, .readability-toggle.active, .ultra-clean-toggle.active, .presenter-toggle.active, .theme-toggle.active { background: #0f172a !important; color: #f8fafc !important; border-color: #0f172a !important; }
        html.dark .density-toggle.active, html.dark .clean-toggle.active, html.dark .readability-toggle.active, html.dark .ultra-clean-toggle.active, html.dark .presenter-toggle.active, html.dark .theme-toggle.active { background: #2563eb !important; border-color: #2563eb !important; color: #eaf2ff !important; }
        body.density-compact .message-cluster { padding: 8px; }
        body.density-compact .turn-row { gap: 8px; }
        body.density-compact .message-card { border-radius: 14px; }
        body.density-compact .message-card.user-card,
        body.density-compact .message-card.assistant-card { padding: 10px; }
        body.density-compact .prose { font-size: 12.5px; line-height: 1.5; }
        body.density-compact .compact-row { padding: 10px; }
        body.density-compact .compact-title { font-size: 14px; }
        body.density-compact .turn-content.user-content { max-width: 620px; }
        body.density-compact .turn-content.assistant-content { max-width: 760px; }
        body.density-comfortable .turn-content.user-content { max-width: 780px; }
        body.density-comfortable .turn-content.assistant-content { max-width: 940px; }
        body.clean-transcript .action-block.tool-action.importance-minor,
        body.clean-transcript .action-block.tool-result.importance-minor,
        body.clean-transcript .action-raw,
        body.clean-transcript .action-kv-grid {
            display: none;
        }
        body.clean-transcript .action-block.tool-result summary .action-meta,
        body.clean-transcript .action-block.tool-action summary .action-meta {
            display: none;
        }
        body.clean-transcript .assistant-entry {
            padding-top: 8px;
        }
        body.ultra-clean .assistant-stream .assistant-entry:not(:last-child) {
            display: none;
        }
        body.ultra-clean .assistant-stream {
            gap: 6px;
            margin-top: 6px;
            padding-left: 8px;
        }
        body.ultra-clean .message-cluster {
            padding: 10px;
        }
        body.ultra-clean .action-block {
            margin: 6px 0;
        }
        body.readability-strict .prose { font-size: 15px; line-height: 1.86; letter-spacing: 0.002em; }
        body.readability-strict .message-card { border-width: 1.5px; }
        body.readability-strict .message-card.assistant-card { border-color: color-mix(in srgb, var(--border) 62%, #64748b 38%); }
        body.readability-strict .message-card.user-card { border-color: #60a5fa; }
        body.readability-strict .role-badge { font-size: 10.5px; letter-spacing: 0.18em; }
        body.readability-strict .action-title { color: #0f172a; }
        body.readability-strict .action-content { font-size: 13px; }
        html.dark body.readability-strict .action-title { color: #e2e8f0; }
        body.presenter-mode aside.w-72 { display: none; }
        body.session-view aside.w-72 { opacity: 0.55; transition: opacity 0.2s ease; }
        body.session-view aside.w-72:hover { opacity: 1; }
        body.session-view .sidebar-link { font-size: 0.8125rem; padding: 0.4rem 0.65rem; }
        body.session-view .sidebar-link.active { box-shadow: none; border-color: #e5e7eb; }
        body.presenter-mode .app-main { width: 100%; }
        body.presenter-mode .app-main > .h-16 { height: 54px; }
        body.presenter-mode .app-main > .h-16 .reload-group,
        body.presenter-mode .app-main > .h-16 #auditScope,
        body.presenter-mode .app-main > .h-16 #auditBtn,
        body.presenter-mode .app-main > .h-16 #cleanToggle,
        body.presenter-mode .app-main > .h-16 #ultraCleanToggle,
        body.presenter-mode .app-main > .h-16 #readabilityToggle,
        body.presenter-mode .app-main > .h-16 #densityToggle,
        body.presenter-mode .app-main > .h-16 #themeToggle,
        body.presenter-mode .app-main > .h-16 #viewMenu {
            display: none !important;
        }
        body.presenter-mode .page-headline { font-size: 40px; line-height: 1.04; }
        body.presenter-mode .meta-line { font-size: 14px; }
        body.presenter-mode .prose { font-size: 17px; line-height: 1.95; }
        body.presenter-mode .message-card.user-card,
        body.presenter-mode .message-card.assistant-card { padding: 18px !important; border-radius: 18px; }
        body.presenter-mode .message-cluster { padding: 18px; border-radius: 18px; }
        body.presenter-mode section.max-w-6xl,
        body.presenter-mode section.max-w-5xl,
        body.presenter-mode section.max-w-4xl { max-width: 92rem; }
        html.dark .text-slate-900, html.dark .text-slate-800, html.dark .text-slate-700 { color: var(--text) !important; }
        html.dark .text-slate-600, html.dark .text-slate-500, html.dark .text-slate-400 { color: var(--text-muted) !important; }
        html.dark .bg-white { background-color: var(--card) !important; }
        html.dark .bg-slate-50, html.dark .bg-slate-100, html.dark .bg-slate-200 { background-color: var(--panel-strong) !important; }
        html.dark .border-slate-200, html.dark .border-slate-300, html.dark [class*='border-slate-200/70'] { border-color: var(--border) !important; }
        html.dark [class*='hover:bg-slate-50']:hover, html.dark [class*='hover:bg-slate-100']:hover { background-color: var(--panel) !important; }
        html.dark input::placeholder { color: var(--muted) !important; }
        html.dark .text-slate-950 { color: var(--text) !important; }

        /* Professional Theme System - SpecStory Quality */
        html[data-theme="catppuccin"] {
            --bg: #1e1e2e; --text: #cdd6f4; --text-muted: #a6adc8;
            --panel: rgba(30, 30, 46, 0.92); --panel-strong: #181825;
            --border: #45475a; --card: #1e1e2e; --main: rgba(24, 24, 37, 0.88);
            --primary: #b4befe; --secondary: #89dceb; --accent: #cba6f7;
            --user-bg: #313244; --user-border: #b4befe; --user-text: #cdd6f4;
            --assistant-bg: #1e1e2e; --assistant-border: #89dceb; --assistant-text: #cdd6f4;
            --code-bg: #0d1117; --code-border: #30363d; --code-text: #cdd6f4;
            --success: #a6e3a1; --warning: #f9e2af; --error: #f38ba8; --info: #89dceb;
        }
        html[data-theme="dracula"] {
            --bg: #282a36; --text: #f8f8f2; --text-muted: #b2b2c6;
            --panel: rgba(40, 42, 54, 0.92); --panel-strong: #21222c;
            --border: #44475a; --card: #282a36; --main: rgba(33, 34, 44, 0.88);
            --primary: #bd93f9; --secondary: #8be9fd; --accent: #ff79c6;
            --user-bg: #44475a; --user-border: #bd93f9; --user-text: #f8f8f2;
            --assistant-bg: #343746; --assistant-border: #8be9fd; --assistant-text: #f8f8f2;
            --code-bg: #282a36; --code-border: #44475a; --code-text: #f8f8f2;
            --success: #50fa7b; --warning: #f1fa8c; --error: #ff5555; --info: #8be9fd;
        }
        html[data-theme="nord"] {
            --bg: #2e3440; --text: #e5e9f0; --text-muted: #a3b1c6;
            --panel: rgba(46, 52, 64, 0.92); --panel-strong: #242933;
            --border: #4c566a; --card: #2e3440; --main: rgba(36, 41, 51, 0.88);
            --primary: #88c0d0; --secondary: #81a1c1; --accent: #b48ead;
            --user-bg: #3b4252; --user-border: #88c0d0; --user-text: #e5e9f0;
            --assistant-bg: #2e3440; --assistant-border: #81a1c1; --assistant-text: #e5e9f0;
            --code-bg: #2e3440; --code-border: #4c566a; --code-text: #e5e9f0;
            --success: #a3be8c; --warning: #ebcb8b; --error: #bf616a; --info: #88c0d0;
        }
        html[data-theme="monokai"] {
            --bg: #272822; --text: #f8f8f2; --text-muted: #a59f85;
            --panel: rgba(39, 40, 34, 0.92); --panel-strong: #1e1f1c;
            --border: #49483e; --card: #272822; --main: rgba(30, 31, 28, 0.88);
            --primary: #a6e22e; --secondary: #66d9ef; --accent: #fd971f;
            --user-bg: #31332c; --user-border: #a6e22e; --user-text: #f8f8f2;
            --assistant-bg: #272822; --assistant-border: #66d9ef; --assistant-text: #f8f8f2;
            --code-bg: #272822; --code-border: #49483e; --code-text: #f8f8f2;
            --success: #a6e22e; --warning: #e6db74; --error: #f92672; --info: #66d9ef;
        }
        html[data-theme="github"] {
            --bg: #0d1117; --text: #c9d1d9; --text-muted: #8b949e;
            --panel: rgba(13, 17, 23, 0.92); --panel-strong: #010409;
            --border: #30363d; --card: #0d1117; --main: rgba(1, 4, 9, 0.88);
            --primary: #58a6ff; --secondary: #79c0ff; --accent: #d2a8ff;
            --user-bg: #161b22; --user-border: #58a6ff; --user-text: #c9d1d9;
            --assistant-bg: #0d1117; --assistant-border: #79c0ff; --assistant-text: #c9d1d9;
            --code-bg: #0d1117; --code-border: #30363d; --code-text: #c9d1d9;
            --success: #3fb950; --warning: #d29922; --error: #f85149; --info: #58a6ff;
        }
        html[data-theme="tokyo"] {
            --bg: #1a1b26; --text: #c0caf5; --text-muted: #9aa5ce;
            --panel: rgba(26, 27, 38, 0.92); --panel-strong: #16161e;
            --border: #414868; --card: #1a1b26; --main: rgba(22, 22, 30, 0.88);
            --primary: #7aa2f7; --secondary: #7dcfff; --accent: #bb9af7;
            --user-bg: #24283b; --user-border: #7aa2f7; --user-text: #c0caf5;
            --assistant-bg: #1a1b26; --assistant-border: #7dcfff; --assistant-text: #c0caf5;
            --code-bg: #1a1b26; --code-border: #414868; --code-text: #c0caf5;
            --success: #9ece6a; --warning: #e0af68; --error: #f7768e; --info: #7dcfff;
        }
        html[data-theme="light"] {
            --bg: #f6f7fb; --text: #0f172a; --text-muted: #64748b;
            --panel: rgba(255, 255, 255, 0.86); --panel-strong: #ffffff;
            --border: #dbe2ea; --card: #ffffff; --main: rgba(247, 250, 255, 0.72);
            --primary: #3b82f6; --secondary: #60a5fa; --accent: #8b5cf6;
            --user-bg: #eef6ff; --user-border: #bfdbfe; --user-text: #0f172a;
            --assistant-bg: #ffffff; --assistant-border: #e5e7eb; --assistant-text: #0f172a;
            --code-bg: #f8fafc; --code-border: #e2e8f0; --code-text: #0f172a;
            --success: #10b981; --warning: #f59e0b; --error: #ef4444; --info: #3b82f6;
        }

        /* Theme-aware code blocks with headers */
        html[data-theme] .prose pre {
            background: var(--code-bg) !important;
            border: 1px solid var(--code-border);
            border-radius: 12px;
            margin: 1.5em 0;
            overflow-x: auto;
        }
        html[data-theme] .prose code {
            background: var(--code-bg);
            color: var(--code-text);
            font-family: "JetBrains Mono", "Fira Code", "SF Mono", Consolas, monospace;
            font-size: 13px;
        }
        html[data-theme] .message-card.user-card {
            background: var(--user-bg);
            border-color: var(--user-border);
            color: var(--user-text);
        }
        html[data-theme] .message-card.assistant-card {
            background: var(--assistant-bg);
            border-color: var(--assistant-border);
            color: var(--assistant-text);
        }

        /* Code block with language header */
        .code-block-wrapper {
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            margin: 1.5em 0;
            background: var(--code-bg);
        }
        .code-block-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 8px 14px;
            background: var(--bg-alt);
            border-bottom: 1px solid var(--border);
            font-size: 11px;
        }
        .code-block-lang {
            font-family: var(--font-family-code);
            color: var(--primary);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }
        .code-block-copy {
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text-muted);
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 10px;
            cursor: pointer;
            transition: all 0.15s ease;
        }
        .code-block-copy:hover {
            background: var(--primary);
            color: var(--bg);
            border-color: var(--primary);
        }

        /* Theme switcher dropdown */
        .theme-dropdown {
            position: relative;
        }
        .theme-dropdown-menu {
            position: absolute;
            right: 0;
            top: calc(100% + 8px);
            min-width: 180px;
            background: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            box-shadow: var(--shadow-lg);
            padding: 8px;
            display: none;
            z-index: 100;
        }
        .theme-dropdown.open .theme-dropdown-menu {
            display: block;
        }
        .theme-option {
            display: flex;
            align-items: center;
            gap: 10px;
            width: 100%;
            padding: 10px 12px;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.15s ease;
            color: var(--text);
            font-size: 13px;
            background: transparent;
            border: none;
            text-align: left;
            font-family: inherit;
        }
        .theme-option:hover {
            background: var(--bg-alt);
        }
        .theme-option.active {
            background: var(--primary);
            color: var(--bg);
        }
        .theme-swatch {
            width: 16px;
            height: 16px;
            border-radius: 4px;
            border: 1px solid var(--border);
        }

        /* Mobile sidebar drawer.
           Explicit CSS rather than Tailwind translate utilities: the
           Tailwind play-CDN does not reliably emit negative-translate
           utilities, so the off-canvas state is driven here directly. */
        #sidebarBackdrop {
            position: fixed;
            inset: 0;
            background: rgba(2, 8, 23, 0.5);
            backdrop-filter: blur(2px);
            z-index: 39;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.2s ease;
        }
        body.sidebar-open #sidebarBackdrop {
            opacity: 1;
            pointer-events: auto;
        }
        /* Below the lg breakpoint the sidebar is an off-canvas drawer. */
        @media (max-width: 1023px) {
            #appSidebar {
                position: fixed;
                inset-block: 0;
                left: 0;
                z-index: 40;
                transform: translateX(-100%);
                transition: transform 0.2s ease;
            }
            body.sidebar-open #appSidebar {
                transform: translateX(0);
            }
        }
        /* lg and up: normal static sidebar, no drawer. */
        @media (min-width: 1024px) {
            #sidebarBackdrop { display: none !important; }
            #appSidebar { transform: none !important; position: static; }
        }
    </style>
    <script nonce="{{ nonce }}">
        /* Theme Switcher */
        (function() {
            const THEME_KEY = 'aihistory-theme';
            const DEFAULT_THEME = 'catppuccin';

            const THEMES = [
                { id: 'catppuccin', name: 'Catppuccin', swatch: '#1e1e2e' },
                { id: 'dracula', name: 'Dracula', swatch: '#282a36' },
                { id: 'nord', name: 'Nord', swatch: '#2e3440' },
                { id: 'monokai', name: 'Monokai', swatch: '#272822' },
                { id: 'github', name: 'GitHub Dark', swatch: '#0d1117' },
                { id: 'tokyo', name: 'Tokyo Night', swatch: '#1a1b26' },
                { id: 'light', name: 'Light', swatch: '#f6f7fb' },
            ];

            function getStoredTheme() {
                try { return localStorage.getItem(THEME_KEY) || DEFAULT_THEME; }
                catch (e) { return DEFAULT_THEME; }
            }

            const DARK_THEMES = ['catppuccin', 'dracula', 'nord', 'monokai', 'github', 'tokyo'];

            function setTheme(themeName) {
                if (!THEMES.find(t => t.id === themeName)) return;
                document.documentElement.setAttribute('data-theme', themeName);
                if (DARK_THEMES.includes(themeName)) {
                    document.documentElement.classList.add('dark');
                } else {
                    document.documentElement.classList.remove('dark');
                }
                try { localStorage.setItem(THEME_KEY, themeName); }
                catch (e) {}
                window.dispatchEvent(new CustomEvent('themechange', { detail: themeName }));
            }

            const storedTheme = getStoredTheme();
            document.documentElement.setAttribute('data-theme', storedTheme);
            if (DARK_THEMES.includes(storedTheme)) {
                document.documentElement.classList.add('dark');
            } else {
                document.documentElement.classList.remove('dark');
            }

            window.aiHistoryTheme = { set: setTheme, get: getStoredTheme, list: THEMES };

            /* Add copy buttons to code blocks */
            document.addEventListener('DOMContentLoaded', function() {
                document.querySelectorAll('.prose pre').forEach(function(pre) {
                    if (pre.parentNode.classList.contains('code-block-wrapper')) return;

                    const wrapper = document.createElement('div');
                    wrapper.className = 'code-block-wrapper';

                    const header = document.createElement('div');
                    header.className = 'code-block-header';

                    const lang = document.createElement('span');
                    lang.className = 'code-block-lang';
                    lang.textContent = pre.className.match(/language-(\\w+)/)?.[1] || 'code';

                    const copyBtn = document.createElement('button');
                    copyBtn.className = 'code-block-copy';
                    copyBtn.textContent = 'Copy';
                    copyBtn.onclick = function() {
                        navigator.clipboard.writeText(pre.textContent).then(function() {
                            copyBtn.textContent = 'Copied!';
                            setTimeout(function() { copyBtn.textContent = 'Copy'; }, 2000);
                        });
                    };

                    header.appendChild(lang);
                    header.appendChild(copyBtn);
                    pre.parentNode.insertBefore(wrapper, pre);
                    wrapper.appendChild(header);
                    wrapper.appendChild(pre);
                });
            });
        })();
    </script>
</head>
<body class="h-screen overflow-hidden">
    <a href="#main-content" class="skip-link">Skip to main content</a>
    <div class="flex h-full">
        <div id="sidebarBackdrop" aria-hidden="true"></div>
        <aside id="appSidebar" class="w-72 border-r border-slate-200/70 app-panel backdrop-blur-xl flex flex-col min-h-0">
            <a href="/" class="p-6 font-semibold text-lg flex items-center gap-3 tracking-tight">
                <div class="w-9 h-9 rounded-xl bg-slate-900 text-white flex items-center justify-center">L</div>
                <span class="text-slate-900 title-font">Lore</span>
            </a>
            <div class="flex-1 px-3 min-h-0 overflow-y-auto space-y-1 pb-4">
                <a href="/" class="sidebar-link {{ 'active' if active=='dashboard' else '' }}">Dashboard</a>
                <a href="/sessions" class="sidebar-link {{ 'active' if active=='sessions' else '' }}">Sessions</a>
                <a href="/projects" class="sidebar-link {{ 'active' if active=='projects' else '' }}">Projects</a>
                <a href="/threads" class="sidebar-link {{ 'active' if active=='threads' else '' }}">Threads</a>
                <a href="/memory" class="sidebar-link {{ 'active' if active=='memory' else '' }}">Memory</a>
                <a href="/stats" class="sidebar-link {{ 'active' if active=='stats' else '' }}">Stats</a>
                <a href="/rules" class="sidebar-link {{ 'active' if active=='rules' else '' }}">Rules</a>
                <a href="/noise-rules" class="sidebar-link {{ 'active' if active=='noise-rules' else '' }}">Noise Rules</a>
                <div class="mt-8 mb-2 px-3 text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">Recent Activity</div>
                <div class="space-y-1">
                    {% for s in recent %}
    <a href="/session/{{ s.id|urlpath }}?back={{ nav_back|urlpath }}" class="sidebar-link text-xs" title="{{ s.display_title or s.title }}">
                        <span class="flex items-center gap-2 min-w-0">
                            <span class="w-6 h-6 rounded-lg border border-slate-200 bg-white flex items-center justify-center text-[10px]" style="color: {{ get_style(s.tool).color }}">{{ get_style(s.tool).icon }}</span>
                            <span class="truncate">{{ s.display_title or s.title or s.id[:12] }}</span>
                        </span>
                    </a>
                    {% endfor %}
                </div>
            </div>
            <div class="mt-auto px-5 py-3 border-t border-slate-200/70 text-[10px] text-slate-500 flex items-center justify-between">
                <span class="font-mono">lore v{{ app_version }}</span>
                <a href="/api/build-info" class="hover:text-slate-700" aria-label="Build info">build</a>
            </div>
        </aside>
        <main id="main-content" class="flex-1 flex flex-col min-w-0 min-h-0 app-main">
            <div class="h-16 border-b border-slate-200/70 app-panel backdrop-blur-xl flex items-center justify-between px-6 sticky top-0 z-20">
                <div class="flex items-center gap-3 w-full max-w-3xl">
                    <button id="sidebarToggle" type="button" aria-label="Open navigation" aria-expanded="false" aria-controls="appSidebar" class="lg:hidden flex-shrink-0 w-9 h-9 rounded-lg border border-slate-200 bg-white text-slate-600 flex items-center justify-center">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/></svg>
                    </button>
                    <div class="flex-1 flex items-center gap-2 bg-white border border-slate-200 rounded-full px-4 py-2 shadow-sm">
                        <svg class="w-4 h-4 text-slate-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
                        <input type="text" onfocus="openSearch()" class="w-full bg-transparent outline-none text-sm text-slate-700" placeholder="Start a new chat across all your AI context...">
                    </div>
                </div>
                <div class="top-controls">
                    <div class="theme-dropdown" id="syncDropdown">
                        <button id="syncBtn" type="button" aria-haspopup="menu" aria-expanded="false" class="density-toggle border rounded-lg px-3 py-1.5 text-xs flex items-center gap-1.5" title="Sync: reload & audit">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg>
                            Sync
                            <svg class="w-3 h-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                        </button>
                        <div class="theme-dropdown-menu !right-0 !left-auto min-w-[180px]" role="menu" aria-label="Sync options">
                            <div class="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500 border-b border-slate-100 dark:border-slate-700">Reload</div>
                            <button onclick="runSync('reload', '')" class="w-full text-left px-3 py-2 text-xs hover:bg-slate-50 dark:hover:bg-slate-700 flex items-center gap-2">
                                <span class="w-2 h-2 rounded-full bg-blue-400"></span>All providers
                            </button>
                            {% for provider in provider_tools %}<button onclick="runSync('reload', '{{ provider }}')" class="w-full text-left px-3 py-2 text-xs hover:bg-slate-50 dark:hover:bg-slate-700 flex items-center gap-2">
                                <span class="w-2 h-2 rounded-full" style="background:{{ get_style(provider).color }}"></span>{{ get_style(provider).name }}
                            </button>{% endfor %}
                            <button onclick="runSync('reload', '', '', true)" class="w-full text-left px-3 py-2 text-[11px] hover:bg-slate-50 dark:hover:bg-slate-700 flex items-center gap-2 text-slate-500 italic" title="Force full rebuild (slow). Use when incremental sync misses changes.">
                                <span class="w-2 h-2 rounded-full bg-amber-400"></span>Full rebuild (slow)
                            </button>
                            <div class="px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500 border-t border-slate-100 dark:border-slate-700 mt-1 pt-1">Audit</div>
                            <button onclick="runSync('audit', '', 'index')" class="w-full text-left px-3 py-2 text-xs hover:bg-slate-50 dark:hover:bg-slate-700 flex items-center gap-2">
                                <span class="w-2 h-2 rounded-full bg-green-400"></span>Quick (index)
                            </button>
                            <button onclick="runSync('audit', '', 'live')" class="w-full text-left px-3 py-2 text-xs hover:bg-slate-50 dark:hover:bg-slate-700 flex items-center gap-2">
                                <span class="w-2 h-2 rounded-full bg-yellow-400"></span>Deep (live)
                            </button>
                        </div>
                    </div>
                    <button id="cancelActionBtn" type="button" aria-label="Cancel" onclick="cancelActiveAction()" class="cancel-toggle border rounded-lg px-3 py-1.5 text-xs" disabled hidden>Cancel</button>
                    {% if show_session_controls %}
                    <details id="viewMenu" class="relative">
                        <summary class="density-toggle border rounded-lg px-3 py-1.5 text-xs list-none cursor-pointer" aria-label="View options">View</summary>
                        <div class="absolute right-0 mt-2 w-40 rounded-xl border border-slate-200 bg-white shadow-xl p-1.5 flex flex-col gap-0.5 z-30">
                            <button id="cleanToggle" type="button" onclick="toggleCleanMode()" class="density-toggle border text-left rounded-lg px-2 py-1.5 text-xs" aria-pressed="false">Clean</button>
                            <button id="ultraCleanToggle" type="button" onclick="toggleUltraClean()" class="density-toggle border text-left rounded-lg px-2 py-1.5 text-xs" aria-pressed="false">Ultra</button>
                            <button id="readabilityToggle" type="button" onclick="toggleReadability()" class="density-toggle border text-left rounded-lg px-2 py-1.5 text-xs" aria-pressed="false">Readable</button>
                            <button id="presenterToggle" type="button" onclick="togglePresenterMode()" class="density-toggle border text-left rounded-lg px-2 py-1.5 text-xs" aria-pressed="false">Present</button>
                            <button id="densityToggle" type="button" onclick="toggleDensity()" class="density-toggle border text-left rounded-lg px-2 py-1.5 text-xs" aria-pressed="false">Compact</button>
                        </div>
                    </details>
                    {% endif %}
                    <div class="theme-dropdown" id="themeDropdown">
                        <button id="themeToggle" type="button" aria-label="Toggle dark mode" aria-pressed="false" aria-haspopup="menu" aria-expanded="false" class="theme-toggle w-9 h-9 rounded-full border text-slate-500 flex items-center justify-center" title="Select theme">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21a4 4 0 01-4-4V5a2 2 0 012-2h4a2 2 0 012 2v12a4 4 0 01-4 4zm0 0h12a2 2 0 002-2v-4a2 2 0 00-2-2h-2.343M11 7.343l1.657-1.657a2 2 0 012.828 0l2.829 2.829a2 2 0 010 2.828l-8.486 8.485M7 17h.01"/></svg>
                        </button>
                        <div class="theme-dropdown-menu" role="menu" aria-label="Theme options">
                            <button type="button" role="menuitemradio" aria-checked="true" class="theme-option active" data-theme="catppuccin" onclick="selectTheme('catppuccin')"><span class="theme-swatch" style="background:#1e1e2e"></span>Catppuccin</button>
                            <button type="button" role="menuitemradio" aria-checked="false" class="theme-option" data-theme="dracula" onclick="selectTheme('dracula')"><span class="theme-swatch" style="background:#282a36"></span>Dracula</button>
                            <button type="button" role="menuitemradio" aria-checked="false" class="theme-option" data-theme="nord" onclick="selectTheme('nord')"><span class="theme-swatch" style="background:#2e3440"></span>Nord</button>
                            <button type="button" role="menuitemradio" aria-checked="false" class="theme-option" data-theme="monokai" onclick="selectTheme('monokai')"><span class="theme-swatch" style="background:#272822"></span>Monokai</button>
                            <button type="button" role="menuitemradio" aria-checked="false" class="theme-option" data-theme="github" onclick="selectTheme('github')"><span class="theme-swatch" style="background:#0d1117"></span>GitHub Dark</button>
                            <button type="button" role="menuitemradio" aria-checked="false" class="theme-option" data-theme="tokyo" onclick="selectTheme('tokyo')"><span class="theme-swatch" style="background:#1a1b26"></span>Tokyo Night</button>
                            <button type="button" role="menuitemradio" aria-checked="false" class="theme-option" data-theme="light" onclick="selectTheme('light')"><span class="theme-swatch" style="background:#f6f7fb"></span>Light</button>
                        </div>
                    </div>
                    <script nonce="{{ nonce }}">
                    (function(){
                      function syncExpanded(dropdownId, btnId){
                        var dd=document.getElementById(dropdownId);
                        var btn=document.getElementById(btnId);
                        if(dd&&btn){btn.setAttribute('aria-expanded',dd.classList.contains('open')?'true':'false');}
                      }
                      window.selectTheme=function(t){
                        window.aiHistoryTheme.set(t);
                        document.querySelectorAll('.theme-option').forEach(function(el){
                          var on=el.dataset.theme===t;
                          el.classList.toggle('active',on);
                          el.setAttribute('aria-checked',on?'true':'false');
                        });
                        document.getElementById('themeDropdown').classList.remove('open');
                        syncExpanded('themeDropdown','themeToggle');
                      };
                      var themeToggle=document.getElementById('themeToggle');
                      if(themeToggle){themeToggle.onclick=function(e){
                        e.stopPropagation();
                        document.getElementById('themeDropdown').classList.toggle('open');
                        syncExpanded('themeDropdown','themeToggle');
                      };}
                      var syncBtn=document.getElementById('syncBtn');
                      if(syncBtn){syncBtn.onclick=function(e){
                        e.stopPropagation();
                        document.getElementById('syncDropdown').classList.toggle('open');
                        syncExpanded('syncDropdown','syncBtn');
                      };}
                      document.addEventListener('click',function(e){
                        if(!e.target.closest('.theme-dropdown')){
                          document.getElementById('themeDropdown').classList.remove('open');
                          var sd=document.getElementById('syncDropdown');
                          if(sd){sd.classList.remove('open');}
                          syncExpanded('themeDropdown','themeToggle');
                          syncExpanded('syncDropdown','syncBtn');
                        }
                      });
                      document.addEventListener('keydown',function(e){
                        if(e.key==='Escape'){
                          var td=document.getElementById('themeDropdown');
                          var sd=document.getElementById('syncDropdown');
                          var open=(td&&td.classList.contains('open'))||(sd&&sd.classList.contains('open'));
                          if(td){td.classList.remove('open');}
                          if(sd){sd.classList.remove('open');}
                          syncExpanded('themeDropdown','themeToggle');
                          syncExpanded('syncDropdown','syncBtn');
                          if(open){var btn=(td&&td.classList.contains('open'))?null:document.getElementById('themeToggle');}
                        }
                      });
                    })();
                    </script>
                </div>
            </div>
            <div class="px-6 pt-2">
                <div id="actionStatus" role="status" aria-live="polite" aria-atomic="true" class="text-[11px] text-slate-500 min-h-[16px]"></div>
            </div>
            <div class="flex-1 min-h-0 overflow-y-auto">
                {% block content %}{% endblock %}
            </div>
        </main>
    </div>
    <div id="searchModal" role="dialog" aria-modal="true" aria-label="Search sessions" aria-hidden="true" class="search-modal fixed inset-0 z-50 bg-black/60 backdrop-blur-sm items-start justify-center pt-[15vh]">
        <div id="searchPanel" class="w-full max-w-xl bg-white border border-slate-200 rounded-xl shadow-2xl overflow-hidden">
            <div class="flex items-center px-4 border-b border-slate-200">
                <input type="text" id="searchInput" aria-label="Search prompts, code, and tools" class="flex-1 bg-transparent border-none p-4 text-sm outline-none text-slate-900" placeholder="Search prompts, code, tools...">
            </div>
            <div id="searchResults" class="max-h-[60vh] overflow-y-auto p-2"></div>
        </div>
    </div>
    <script src="/static/highlight-11.9.0.min.js"></script>
    <script nonce="{{ nonce }}">
        if (typeof window.hljs !== 'undefined') {
            window.hljs.configure({ ignoreUnescapedHTML: true });
        }
        function initCodeBlocks() {
            if (typeof window.hljs === 'undefined') {
                return;
            }
            document.querySelectorAll('pre code').forEach((el) => {
                if (!el.dataset.highlighted) {
                    hljs.highlightElement(el);
                    el.dataset.highlighted = "true";
                    const pre = el.parentElement;
                    const lines = el.innerText.split('\\n').length;
                    const isLong = pre.scrollHeight > 400 || lines > 20;

                    if (isLong) {
                        pre.classList.add('collapsed');
                        const expandBtn = document.createElement('button');
                        expandBtn.className = 'absolute bottom-2 left-1/2 -translate-x-1/2 text-[11px] bg-white border border-slate-300 hover:border-slate-400 px-3 py-1.5 rounded-lg shadow-sm transition-all z-10';
                        expandBtn.innerHTML = '↓ Show More';
                        expandBtn.onclick = (e) => {
                            e.stopPropagation();
                            if (pre.classList.contains('collapsed')) {
                                pre.classList.remove('collapsed');
                                expandBtn.innerHTML = '↑ Show Less';
                            } else {
                                pre.classList.add('collapsed');
                                expandBtn.innerHTML = '↓ Show More';
                                pre.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
                            }
                        };
                        pre.style.position = 'relative';
                        pre.appendChild(expandBtn);
                    }

                    const copyBtn = document.createElement('button');
                    copyBtn.className = 'absolute top-2 right-2 text-[10px] text-zinc-500 hover:text-white bg-zinc-900/80 px-2 py-1 rounded border border-zinc-800 opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity z-10';
                    copyBtn.textContent = 'Copy';
                    copyBtn.setAttribute('aria-label', 'Copy code block');
                    copyBtn.onclick = () => { navigator.clipboard.writeText(el.innerText); copyBtn.textContent = 'Copied!'; setTimeout(()=>copyBtn.textContent='Copy', 2000); };
                    pre.classList.add('group', 'relative');

                    if (el.className.includes('language-diff') || el.innerText.startsWith('*** Begin Patch') || el.innerText.includes('@@')) {
                        pre.classList.add('diff-block');
                    }

                    if (!pre.parentElement.classList.contains('code-card')) {
                        const wrapper = document.createElement('div');
                        wrapper.className = 'code-card';
                        const header = document.createElement('div');
                        header.className = 'code-card-header';
                        let title = 'Code Block';
                        const classText = String(el.className || '');
                        const langMatch = classText.match(/language-([\\w-]+)/i);
                        const language = langMatch ? langMatch[1].toLowerCase() : '';
                        const firstLine = (el.innerText.split('\\n').find((line) => line.trim()) || '').trim();
                        const prev = pre.previousElementSibling;
                        if (prev && /Update:/.test(prev.textContent || "")) {
                            const match = prev.textContent.match(/Update:\\s*`([^`]+)`/);
                            if (match) title = `Update: ${match[1]}`;
                        } else if (language === 'bash' || language === 'sh' || language === 'zsh') {
                            title = 'Shell Command';
                        } else if (language === 'json') {
                            title = 'JSON Payload';
                        } else if (language === 'sql') {
                            title = 'SQL Query';
                        } else if (language === 'diff' || firstLine.startsWith('*** Begin Patch') || firstLine.startsWith('diff --git') || firstLine.startsWith('@@')) {
                            title = 'Patch Diff';
                        } else if (language === 'yaml' || language === 'yml') {
                            title = 'YAML Config';
                        }
                        const titleEl = document.createElement('span');
                        titleEl.className = 'code-card-title';
                        titleEl.textContent = title;
                        const metaEl = document.createElement('span');
                        metaEl.className = 'code-card-meta';
                        metaEl.textContent = `${lines} lines`;
                        header.appendChild(titleEl);
                        header.appendChild(metaEl);
                        pre.parentElement.insertBefore(wrapper, pre);
                        wrapper.appendChild(header);
                        wrapper.appendChild(pre);
                    }
                    pre.appendChild(copyBtn);
                }
            });
        }
        document.addEventListener('DOMContentLoaded', initCodeBlocks);

        /* Reusable focus-trap helper for modal dialogs */
        window.FocusTrap = (function () {
            const FOCUSABLE = [
                'a[href]', 'button:not([disabled])', 'textarea:not([disabled])',
                'input:not([disabled]):not([type="hidden"])', 'select:not([disabled])',
                '[tabindex]:not([tabindex="-1"])'
            ].join(',');
            const PAGE_SELECTORS = ['.flex.h-full'];

            function getFocusable(container) {
                return Array.from(container.querySelectorAll(FOCUSABLE)).filter((el) => {
                    return el.offsetWidth > 0 || el.offsetHeight > 0 || el === document.activeElement;
                });
            }

            function activate(dialog, opts) {
                opts = opts || {};
                const previouslyFocused = document.activeElement;
                const pageRoots = PAGE_SELECTORS
                    .map((sel) => document.querySelector(sel))
                    .filter((el) => el && !el.contains(dialog));
                pageRoots.forEach((el) => {
                    el.setAttribute('inert', '');
                    el.setAttribute('aria-hidden', 'true');
                });

                function onKeydown(e) {
                    if (e.key !== 'Tab') return;
                    const focusable = getFocusable(dialog);
                    if (focusable.length === 0) {
                        e.preventDefault();
                        return;
                    }
                    const first = focusable[0];
                    const last = focusable[focusable.length - 1];
                    if (e.shiftKey && document.activeElement === first) {
                        e.preventDefault();
                        last.focus();
                    } else if (!e.shiftKey && document.activeElement === last) {
                        e.preventDefault();
                        first.focus();
                    }
                }
                dialog.addEventListener('keydown', onKeydown);

                const initial = opts.initialFocus || getFocusable(dialog)[0] || dialog;
                requestAnimationFrame(() => {
                    if (initial && typeof initial.focus === 'function') initial.focus();
                });

                return function release() {
                    dialog.removeEventListener('keydown', onKeydown);
                    pageRoots.forEach((el) => {
                        el.removeAttribute('inert');
                        el.removeAttribute('aria-hidden');
                    });
                    if (previouslyFocused && typeof previouslyFocused.focus === 'function') {
                        previouslyFocused.focus();
                    }
                };
            }

            return { activate: activate };
        })();

        let searchTrapRelease = null;
        function openSearch() {
            const modal = document.getElementById('searchModal');
            const panel = document.getElementById('searchPanel');
            const input = document.getElementById('searchInput');
            if (!modal || !input) return;
            modal.classList.add('open');
            modal.setAttribute('aria-hidden', 'false');
            if (searchTrapRelease) { searchTrapRelease(); searchTrapRelease = null; }
            searchTrapRelease = window.FocusTrap.activate(panel || modal, { initialFocus: input });
            requestAnimationFrame(() => {
                input.focus();
                input.select();
            });
        }
        function closeSearch() {
            const modal = document.getElementById('searchModal');
            if (!modal || !modal.classList.contains('open')) return;
            modal.classList.remove('open');
            modal.setAttribute('aria-hidden', 'true');
            if (searchTrapRelease) { searchTrapRelease(); searchTrapRelease = null; }
        }
        document.addEventListener('keydown', e => {
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault();
                openSearch();
            }
            if (e.key === 'Escape') closeSearch();
        });
        document.addEventListener('click', (e) => {
            const modal = document.getElementById('searchModal');
            if (!modal) return;
            if (e.target === modal) closeSearch();
        });
        function escapeHtml(value) {
            return String(value ?? '').replace(/[&<>"']/g, (char) => ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#39;'
            }[char] || char));
        }
        let debounce;
        const searchInputEl = document.getElementById('searchInput');
        const searchResultsEl = document.getElementById('searchResults');
        if (searchInputEl && searchResultsEl) {
            searchInputEl.addEventListener('input', e => {
                clearTimeout(debounce);
                const q = e.target.value.trim();
                if (q.length < 2) return;
                debounce = setTimeout(() => {
                    const apiUrl = new URL('/api/search', window.location.origin);
                    apiUrl.searchParams.set('q', q);
                    fetch(apiUrl.toString(), { credentials: 'same-origin' }).then(r=>r.json()).then(data => {
                        if (!Array.isArray(data)) {
                            searchResultsEl.innerHTML = '';
                            return;
                        }
                        searchResultsEl.innerHTML = data.map(s => {
                            const sid = encodeURIComponent(String(s.id || ''));
                            const label = escapeHtml(s.title || s.id || 'Untitled Session');
                            const tool = escapeHtml(s.tool || 'unknown');
                            const date = escapeHtml(s.date || '');
                            return `<a href="/session/${sid}" class="block p-3 rounded-lg hover:bg-slate-100 group"><div class="text-sm font-medium text-slate-900 group-hover:text-blue-600 transition-colors">${label}</div><div class="text-[10px] text-slate-500 mt-1">${tool} • ${date}</div></a>`;
                        }).join('');
                    }).catch(() => {
                        searchResultsEl.innerHTML = '';
                    });
                }, 200);
            });
        }
        function copyCommand(cmd) {
            navigator.clipboard.writeText(cmd);
        }
        function copyLink(url) {
            navigator.clipboard.writeText(url);
        }

        function setActionStatus(message) {
            const el = document.getElementById('actionStatus');
            if (el) el.textContent = message || '';
        }

        function showErrorToast(title, message) {
            const existing = document.getElementById('errorToast');
            if (existing) existing.remove();
            const toast = document.createElement('div');
            toast.id = 'errorToast';
            toast.setAttribute('role', 'alert');
            toast.className = 'fixed bottom-4 right-4 max-w-md bg-red-50 border border-red-200 rounded-xl shadow-2xl p-4 z-50';
            const safeTitle = String(title || 'Error');
            const safeMessage = String(message || 'Unexpected error');
            toast.innerHTML = `<div class="flex items-start gap-3"><div class="text-red-600" aria-hidden="true">!</div><div class="flex-1"><div class="text-sm font-semibold text-red-900">${escapeHtml(safeTitle)}</div><div class="text-sm text-red-700 mt-1">${escapeHtml(safeMessage)}</div></div><button type="button" class="text-red-500 hover:text-red-700" aria-label="Close error" onclick="this.closest('#errorToast').remove()"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 6l12 12M18 6L6 18"/></svg></button></div>`;
            document.body.appendChild(toast);
            setTimeout(() => {
                const current = document.getElementById('errorToast');
                if (current) current.remove();
            }, 10000);
        }

        let activeActionJobId = '';

        function setActiveActionJob(jobId) {
            activeActionJobId = jobId || '';
            const btn = document.getElementById('cancelActionBtn');
            if (btn) {
                btn.disabled = !activeActionJobId;
            }
        }

        async function cancelActiveAction() {
            if (!activeActionJobId) return;
            const btn = document.getElementById('cancelActionBtn');
            const original = btn ? btn.textContent : 'Cancel';
            if (btn) {
                btn.disabled = true;
                btn.textContent = 'Cancelling...';
            }
            try {
                const response = await fetch(`/api/action-cancel/${encodeURIComponent(activeActionJobId)}`, {
                    method: 'POST',
                    credentials: 'same-origin',
                });
                const payload = await response.json();
                if (!response.ok) throw new Error(payload.error || 'Cancel failed');
                setActionStatus(payload.message || 'Cancellation requested');
            } catch (error) {
                setActionStatus(`Cancel failed: ${error.message}`);
                showErrorToast('Cancel failed', error.message);
            } finally {
                if (btn) btn.textContent = original;
            }
        }

        function getSelectedProvider() {
            const select = document.getElementById('reloadProviderScope');
            return (select?.value || '').trim();
        }

        function initReloadProviderScope() {
            const select = document.getElementById('reloadProviderScope');
            if (!select) return;
            const params = new URLSearchParams(window.location.search || '');
            const toolFromUrl = (params.get('tool') || '').trim();
            const availableValues = new Set(Array.from(select.options).map((opt) => String(opt.value || '').trim()));

            let selected = '';
            if (toolFromUrl && availableValues.has(toolFromUrl)) {
                selected = toolFromUrl;
            } else {
                try {
                    const saved = (localStorage.getItem('aihistory-reload-provider') || '').trim();
                    if (saved && availableValues.has(saved)) selected = saved;
                } catch (_) {}
            }

            if (!selected && availableValues.has('opencode')) {
                selected = 'opencode';
            }

            if (selected) {
                select.value = selected;
            }

            select.addEventListener('change', () => {
                try {
                    localStorage.setItem('aihistory-reload-provider', (select.value || '').trim());
                } catch (_) {}
            });
        }

        function sleep(ms) {
            return new Promise((resolve) => setTimeout(resolve, ms));
        }

        async function pollActionJob({ jobId, statusPath, onProgress, timeoutMs = 180000 }) {
            if (!jobId || !statusPath) throw new Error('Missing job polling configuration');
            const startedAt = Date.now();
            let delayMs = 700;
            const maxDelayMs = 2000;
            while (true) {
                if (Date.now() - startedAt > timeoutMs) {
                    throw new Error('Timed out waiting for background action');
                }
                const statusResponse = await fetch(`${statusPath}/${encodeURIComponent(jobId)}`, { credentials: 'same-origin' });
                const state = await statusResponse.json();
                if (!statusResponse.ok) throw new Error(state.error || 'Failed to read action status');
                if (typeof onProgress === 'function') onProgress(state);
                if (state.status === 'done') return state;
                if (state.status === 'cancelled') throw new Error(state.message || 'Cancelled');
                if (state.status === 'error') throw new Error(state.error || state.message || 'Action failed');
                await sleep(delayMs);
                delayMs = Math.min(maxDelayMs, Math.floor(delayMs * 1.25));
            }
            }

            async function runSync(action, provider, scope, full) {
            const btn = document.getElementById('syncBtn');
            const cancelBtn = document.getElementById('cancelActionBtn');
            if (!btn) return;
            btn.disabled = true;
            btn.innerHTML = '<svg class="w-3.5 h-3.5 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg> Syncing...';
            if (cancelBtn) { cancelBtn.hidden = false; cancelBtn.disabled = false; }
            const startedAt = Date.now();
            const actionLabel = full ? `${action} (full)` : action;
            setActionStatus(`Starting ${actionLabel}...`);
            closeAllDropdowns();
            try {
                const isReload = action === 'reload';
                const auditScope = scope || 'index';
                const url = new URL(isReload ? '/api/reload-sessions' : '/api/audit', window.location.origin);
                url.searchParams.set('async', '1');
                if (provider) url.searchParams.set('provider', provider);
                if (isReload && full) url.searchParams.set('full', '1');
                if (!isReload) url.searchParams.set('scope', auditScope);
                const httpMethod = isReload ? 'POST' : 'GET';
                const response = await fetch(url.toString(), { method: httpMethod, credentials: 'same-origin' });
                const payload = await response.json();
                if (!response.ok) throw new Error(payload.error || `${action} failed`);
                const jobId = payload.job_id;
                if (!jobId) throw new Error(`Missing ${action} job id`);
                setActiveActionJob(jobId);
                const finalState = await pollActionJob({
                    jobId,
                    statusPath: isReload ? '/api/reload-status' : '/api/audit-status',
                    onProgress: (state) => {
                        const progress = Number(state.progress || 0);
                        const message = state.message || (isReload ? 'Reloading' : 'Auditing');
                        const elapsed = Math.max(0, Math.floor((Date.now() - startedAt) / 1000));
                        setActionStatus(`${message} (${progress}%) • ${elapsed}s`);
                    }
                });
                if (isReload) {
                    setActionStatus('Reload complete. Refreshing view...');
                    window.location.reload();
                } else {
                    const result = finalState.result || {};
                    const issues = result?.totals?.issues ?? 0;
                    const sessions = result?.totals?.sessions ?? 0;
                    setActionStatus(`Audit finished: ${sessions} sessions, issues: ${issues}, uniform=${result.uniform ? 'yes' : 'no'}`);
                }
            } catch (error) {
                setActionStatus(`${action.charAt(0).toUpperCase() + action.slice(1)} failed: ${error.message}`);
                showErrorToast(`${action} failed`, error.message);
            } finally {
                setActiveActionJob('');
                btn.disabled = false;
                btn.innerHTML = '<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg> Sync <svg class="w-3 h-3 opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>';
                if (cancelBtn) { cancelBtn.hidden = true; cancelBtn.disabled = true; }
            }
        }

        function closeAllDropdowns() {
            document.querySelectorAll('.theme-dropdown-menu').forEach(m => m.classList.remove('open'));
            document.querySelectorAll('details[open]').forEach(d => d.removeAttribute('open'));
        }

        async function reloadSessions() {
            const btn = document.getElementById('reloadBtn');
            const label = btn ? btn.textContent : '';
            const provider = getSelectedProvider();
            const startedAt = Date.now();
            if (btn) { btn.disabled = true; btn.textContent = 'Reloading...'; }
            setActionStatus('Starting reload...');
            try {
                const url = new URL('/api/reload-sessions', window.location.origin);
                url.searchParams.set('async', '1');
                if (provider) url.searchParams.set('provider', provider);
                const response = await fetch(url.toString(), { method: 'POST', credentials: 'same-origin' });
                const payload = await response.json();
                if (!response.ok) throw new Error(payload.error || 'Reload failed');
                const jobId = payload.job_id;
                if (!jobId) throw new Error('Missing reload job id');
                setActiveActionJob(jobId);
                await pollActionJob({
                    jobId,
                    statusPath: '/api/reload-status',
                    onProgress: (state) => {
                        const progress = Number(state.progress || 0);
                        const message = state.message || 'Reloading';
                        const elapsed = Math.max(0, Math.floor((Date.now() - startedAt) / 1000));
                        if (btn) btn.textContent = `Reload ${progress}%`;
                        setActionStatus(`${message} (${progress}%) • ${elapsed}s`);
                    }
                });
                setActionStatus('Reload complete. Refreshing view...');
                window.location.reload();
            } catch (error) {
                setActionStatus(`Reload failed: ${error.message}`);
                showErrorToast('Reload failed', error.message);
            } finally {
                setActiveActionJob('');
                if (btn) { btn.disabled = false; btn.textContent = label || 'Reload'; }
            }
        }

        async function runUniformityAudit() {
            const btn = document.getElementById('auditBtn');
            const original = btn ? btn.textContent : '';
            const provider = getSelectedProvider();
            const scope = (document.getElementById('auditScope')?.value || 'index').trim();
            const startedAt = Date.now();
            if (btn) { btn.disabled = true; btn.textContent = 'Auditing...'; }
            setActionStatus('Starting audit...');
            try {
                const url = new URL('/api/audit', window.location.origin);
                url.searchParams.set('scope', scope || 'index');
                url.searchParams.set('async', '1');
                if (provider) url.searchParams.set('provider', provider);
                const response = await fetch(url.toString(), { credentials: 'same-origin' });
                const payload = await response.json();
                if (!response.ok) throw new Error(payload.error || 'Audit failed');
                const jobId = payload.job_id;
                if (!jobId) throw new Error('Missing audit job id');
                setActiveActionJob(jobId);
                const finalState = await pollActionJob({
                    jobId,
                    statusPath: '/api/audit-status',
                    onProgress: (state) => {
                        const progress = Number(state.progress || 0);
                        const message = state.message || 'Auditing';
                        const elapsed = Math.max(0, Math.floor((Date.now() - startedAt) / 1000));
                        if (btn) btn.textContent = `Audit ${progress}%`;
                        setActionStatus(`${message} (${progress}%) • ${elapsed}s`);
                    }
                });
                const result = finalState.result || {};
                const issues = result?.totals?.issues ?? 0;
                const sessions = result?.totals?.sessions ?? 0;
                setActionStatus(`Audit ${scope} finished: ${sessions} sessions, ${issues} issues, uniform=${result.uniform ? 'yes' : 'no'}`);
                console.log('ai-history audit', result);
            } catch (error) {
                setActionStatus(`Audit failed: ${error.message}`);
                showErrorToast('Audit failed', error.message);
            } finally {
                setActiveActionJob('');
                if (btn) { btn.disabled = false; btn.textContent = original || 'Audit'; }
            }
        }
        function syncSessionControlVisibility() {
            const hasTranscriptView = Boolean(
                document.querySelector('[data-transcript-view="1"]')
            );
            document.body.classList.toggle('session-view', hasTranscriptView);
            const viewMenu = document.getElementById('viewMenu');
            if (viewMenu) {
                viewMenu.style.display = hasTranscriptView ? '' : 'none';
                if (!hasTranscriptView) {
                    viewMenu.removeAttribute('open');
                }
            }
            const controlIds = [
                'cleanToggle',
                'ultraCleanToggle',
                'readabilityToggle',
                'presenterToggle',
                'densityToggle',
            ];
            controlIds.forEach((id) => {
                const node = document.getElementById(id);
                if (!node) {
                    return;
                }
                node.style.display = hasTranscriptView ? '' : 'none';
                node.disabled = !hasTranscriptView;
                node.setAttribute('aria-hidden', hasTranscriptView ? 'false' : 'true');
            });
        }
        function applyDensity(mode) {
            if (mode === 'compact') {
                document.body.classList.add('density-compact');
                document.body.classList.remove('density-comfortable');
                document.body.dataset.density = 'compact';
            } else {
                document.body.classList.remove('density-compact');
                document.body.classList.add('density-comfortable');
                document.body.dataset.density = 'comfortable';
            }
            try { localStorage.setItem('aihistory-density', mode); } catch (_) {}
            const toggle = document.getElementById('densityToggle');
            if (toggle) toggle.textContent = mode === 'compact' ? 'Comfortable' : 'Compact';
            if (toggle) toggle.classList.toggle('active', mode === 'compact');
            if (toggle) toggle.setAttribute('aria-pressed', mode === 'compact' ? 'true' : 'false');
        }
        function toggleDensity() {
            const compact = document.body.classList.contains('density-compact');
            applyDensity(compact ? 'comfortable' : 'compact');
        }
        function applyCleanMode(mode) {
            const clean = mode === 'clean';
            document.body.classList.toggle('clean-transcript', clean);
            try { localStorage.setItem('aihistory-clean-mode', clean ? 'clean' : 'full'); } catch (_) {}
            const toggle = document.getElementById('cleanToggle');
            if (toggle) toggle.textContent = clean ? 'Full' : 'Clean';
            if (toggle) toggle.classList.toggle('active', clean);
            if (toggle) toggle.setAttribute('aria-pressed', clean ? 'true' : 'false');
        }
        function toggleCleanMode() {
            const clean = document.body.classList.contains('clean-transcript');
            applyCleanMode(clean ? 'full' : 'clean');
        }
        function setToolDetailsCollapsed(collapsed) {
            document.querySelectorAll('details.action-block').forEach((el) => {
                if (collapsed) {
                    el.removeAttribute('open');
                }
            });
        }
        function applyUltraClean(mode) {
            const ultra = mode === 'on';
            document.body.classList.toggle('ultra-clean', ultra);
            try { localStorage.setItem('aihistory-ultra-clean', ultra ? 'on' : 'off'); } catch (_) {}
            const toggle = document.getElementById('ultraCleanToggle');
            if (toggle) toggle.textContent = ultra ? 'Normal' : 'Ultra';
            if (toggle) toggle.classList.toggle('active', ultra);
            if (toggle) toggle.setAttribute('aria-pressed', ultra ? 'true' : 'false');
            if (ultra) {
                setToolDetailsCollapsed(true);
            }
        }
        function toggleUltraClean() {
            const ultra = document.body.classList.contains('ultra-clean');
            applyUltraClean(ultra ? 'off' : 'on');
        }
        function applyPresenterMode(mode) {
            const presenter = mode === 'on';
            document.body.classList.toggle('presenter-mode', presenter);
            try { localStorage.setItem('aihistory-presenter-mode', presenter ? 'on' : 'off'); } catch (_) {}
            const toggle = document.getElementById('presenterToggle');
            if (toggle) toggle.textContent = presenter ? 'Exit' : 'Present';
            if (toggle) toggle.classList.toggle('active', presenter);
            if (toggle) toggle.setAttribute('aria-pressed', presenter ? 'true' : 'false');
        }
        function togglePresenterMode() {
            const presenter = document.body.classList.contains('presenter-mode');
            applyPresenterMode(presenter ? 'off' : 'on');
        }
        function applyReadability(mode) {
            const strict = mode === 'strict';
            document.body.classList.toggle('readability-strict', strict);
            try { localStorage.setItem('aihistory-readability', strict ? 'strict' : 'standard'); } catch (_) {}
            const toggle = document.getElementById('readabilityToggle');
            if (toggle) toggle.textContent = strict ? 'Standard' : 'Readable';
            if (toggle) toggle.classList.toggle('active', strict);
            if (toggle) toggle.setAttribute('aria-pressed', strict ? 'true' : 'false');
        }
        function toggleReadability() {
            const strict = document.body.classList.contains('readability-strict');
            applyReadability(strict ? 'standard' : 'strict');
        }
        function applyTheme(mode) {
            if (mode === 'dark') {
                document.documentElement.classList.add('dark');
            } else {
                document.documentElement.classList.remove('dark');
            }
            try { localStorage.setItem('aihistory-theme', mode); } catch (_) {}
            const toggle = document.getElementById('themeToggle');
            if (toggle) toggle.textContent = mode === 'dark' ? '☀' : '◐';
            if (toggle) toggle.setAttribute('aria-pressed', mode === 'dark' ? 'true' : 'false');
            if (toggle) toggle.classList.toggle('active', mode === 'dark');
        }
        document.addEventListener('DOMContentLoaded', () => {
            const currentTheme = window.aiHistoryTheme?.get() || 'catppuccin';
            document.querySelectorAll('.theme-option').forEach(function(el) {
                el.classList.toggle('active', el.dataset.theme === currentTheme);
            });
            const themeToggle = document.getElementById('themeToggle');
            try {
                applyDensity(localStorage.getItem('aihistory-density') || 'comfortable');
                applyCleanMode(localStorage.getItem('aihistory-clean-mode') || 'full');
                applyUltraClean(localStorage.getItem('aihistory-ultra-clean') || 'off');
                applyReadability(localStorage.getItem('aihistory-readability') || 'standard');
                applyPresenterMode(localStorage.getItem('aihistory-presenter-mode') || 'off');
            } catch (_) {}
            document.querySelectorAll('form[data-autosubmit="true"] select, form[data-autosubmit="true"] input[type="date"]').forEach((el) => {
                el.addEventListener('change', () => {
                    if (!el.form) return;
                    if (typeof el.form.requestSubmit === 'function') {
                        el.form.requestSubmit();
                    } else {
                        el.form.submit();
                    }
                });
            });
            initReloadProviderScope();
        });
        function initTocSpy() {
            const items = Array.from(document.querySelectorAll('[data-toc]'));
            if (!items.length) return;
            const tocList = document.querySelector('.toc-list');
            const observer = new IntersectionObserver((entries) => {
                const visible = entries.filter(e => e.isIntersecting).sort((a,b)=>b.intersectionRatio-a.intersectionRatio)[0];
                if (!visible) return;
                items.forEach(i => i.classList.remove('active'));
                const target = items.find(i => i.dataset.toc === visible.target.id);
                if (target) {
                    target.classList.add('active');
                    if (tocList) target.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
                }
            }, { rootMargin: '0px 0px -70% 0px', threshold: [0.1, 0.25, 0.5] });
            items.forEach(item => {
                const target = document.getElementById(item.dataset.toc);
                if (target) observer.observe(target);
            });
        }
        document.addEventListener('DOMContentLoaded', initTocSpy);
    </script>
    <script nonce="{{ nonce }}">
        (function () {
            const toggle = document.getElementById('sidebarToggle');
            const sidebar = document.getElementById('appSidebar');
            const backdrop = document.getElementById('sidebarBackdrop');
            if (!toggle || !sidebar) return;
            function openSidebar() {
                document.body.classList.add('sidebar-open');
                toggle.setAttribute('aria-expanded', 'true');
            }
            function closeSidebar() {
                document.body.classList.remove('sidebar-open');
                toggle.setAttribute('aria-expanded', 'false');
            }
            toggle.addEventListener('click', function () {
                if (document.body.classList.contains('sidebar-open')) {
                    closeSidebar();
                } else {
                    openSidebar();
                }
            });
            if (backdrop) backdrop.addEventListener('click', closeSidebar);
            document.addEventListener('keydown', function (e) {
                if (e.key === 'Escape' && document.body.classList.contains('sidebar-open')) {
                    closeSidebar();
                }
            });
            sidebar.querySelectorAll('a').forEach(function (link) {
                link.addEventListener('click', closeSidebar);
            });
        })();
    </script>
</body>
</html>
"""

SESSION_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div data-transcript-view="1" hidden></div>
<section class="max-w-[90rem] mx-auto px-6 pt-6 pb-4">
    <div class="surface-card flex flex-wrap items-center justify-between gap-4 px-5 py-4 backdrop-blur-xl">
        <div class="min-w-0">
            <h1 class="session-headline truncate">{{ session.title or 'Untitled Session' }}</h1>
            <div class="session-meta mt-2">
                <span>{{ session.created_at.strftime('%b %d') }}</span>
                <span class="session-meta-dot"></span>
                <span>via {{ style.name }}</span>
                <span class="session-meta-dot"></span>
                <span>{{ session.prompt_count }} prompts</span>
                <span class="session-meta-dot"></span>
                <span>{{ project_label(session.project_path) }}</span>
            </div>
            {% if session.thread_id %}
            <div class="flex flex-wrap gap-2 mt-3">
                <a href="/thread/{{ session.thread_id|urlpath }}" class="pill bg-white border border-slate-200 text-slate-500 font-mono hover:text-slate-900 transition-colors">{{ session.thread_id[-10:] }}</a>
            </div>
            {% endif %}
        </div>
        <div class="flex flex-wrap items-center gap-2">
            {% if session.thread_id %}
            <button onclick='copyCommand({{ ("ai-session switch gemini --thread-id " ~ session.thread_id)|tojson }})' class="text-[11px] text-slate-500 hover:text-slate-900 border border-slate-200 px-3 py-1.5 rounded-xl transition-all bg-white">Copy Continue</button>
            {% endif %}
            <button onclick="copyLink(window.location.href)" class="text-[11px] text-slate-500 hover:text-slate-900 border border-slate-200 px-3 py-1.5 rounded-xl transition-all bg-white">Copy Link</button>
            <button onclick="resumeSession({{ session.session_id|tojson }})" class="text-[11px] text-blue-600 hover:text-blue-900 border border-blue-200 px-3 py-1.5 rounded-xl transition-all bg-white">Resume</button>
            <a href="/" class="text-[11px] text-slate-500 hover:text-slate-900 border border-slate-200 px-3 py-1.5 rounded-xl transition-all bg-white">Dashboard</a>
            <a href="/export/{{ session.session_id|urlpath }}" class="text-[11px] text-slate-500 hover:text-slate-900 border border-slate-200 px-3 py-1.5 rounded-xl transition-all bg-white">Export MD</a>
            <form action="/session/{{ session.session_id|urlpath }}/delete" method="POST" onsubmit="return confirm('Are you sure you want to delete this session? This action cannot be undone.');" style="display:inline;">
                <input type="hidden" name="next" value="{{ back_target or '/sessions' }}">
                <button type="submit" class="text-[11px] text-red-600 hover:text-red-900 border border-red-200 px-3 py-1.5 rounded-xl transition-all bg-white">Delete</button>
            </form>
        </div>
    </div>
</section>

<section class="max-w-[90rem] mx-auto px-6 pb-24">
    <div class="flex flex-col lg:flex-row w-full">
    <aside class="hidden lg:block lg:flex-grow lg:flex-shrink-[100] lg:basis-[550px] lg:min-w-[350px] lg:max-w-[550px] lg:pr-6">
        <div class="toc-card sticky top-24 h-[calc(100vh-12rem)]">
            <div class="toc-card-head">On this page</div>
            <nav aria-label="Table of contents">
            <ol class="toc-stepper toc-list space-y-0.5">
                {% for item in toc_items %}
                <li>
                <a href="#msg-{{ item.index }}" class="toc-item" data-toc="msg-{{ item.index }}" title="{{ item.text }}">
                    <span class="toc-badge">{{ loop.index }}</span>
                    <span class="toc-item-text">{{ item.text }}</span>
                    <span class="toc-item-meta">{{ item.time }}</span>
                </a>
                </li>
                {% endfor %}
                {% if toc_items|length == 0 %}
                <li class="text-[11px] text-slate-500 px-3 py-2">No prompts detected.</li>
                {% endif %}
            </ol>
            </nav>
            <div class="toc-card-foot">{{ session.prompt_count }} prompts</div>
        </div>
    </aside>
        <div class="lg:flex-grow-0 lg:flex-shrink-1 lg:basis-[850px] lg:min-w-[500px] lg:px-8 space-y-6">
        {% for pair in session.pairs %}
        <div class="message-cluster">
            {% if pair.user %}
            <div id="msg-{{ pair.user.index }}" class="turn-row user group">
                <div class="turn-gutter">
                    <span class="turn-index user">{{ loop.index }}</span>
                </div>
                <div class="turn-content user-content">
                    <div class="flex items-center justify-between mb-2">
                        <div class="role-badge">
                            <span class="prompt-icon" title="You">You</span>
                            <span>Prompt</span>
                        </div>
                        <div class="text-[10px] text-slate-500 font-mono opacity-60">{{ pair.user.timestamp.strftime('%H:%M') }}</div>
                    </div>
                    <div class="message-card user-card p-4">
                        <div class="prose max-w-none antialiased">
                            {% if pair.user.formatted_reasoning %} {{ pair.user.formatted_reasoning | safe }} {% endif %}
                            {{ pair.user.formatted_content | safe }}
                        </div>
                    </div>
                </div>
            </div>
            {% endif %}
            <div class="assistant-stream">
            {% for resp in pair.responses %}
            <div class="assistant-entry turn-row assistant group">
                <div class="turn-gutter">
                    <span class="turn-index assistant">A</span>
                </div>
                <div class="turn-content assistant-content">
                    <div class="flex items-center justify-between mb-2">
                        <div class="role-badge">
                            <span class="response-icon" title="{{ style.name }}">AI</span>
                            <span>{{ style.name }}</span>
                        </div>
                        <div class="message-time">{{ resp.timestamp.strftime('%H:%M') }}</div>
                    </div>
                    <div class="message-card assistant-card p-4">
                        <div class="prose max-w-none antialiased">
                            {% if resp.formatted_reasoning %} {{ resp.formatted_reasoning | safe }} {% endif %}
                            {{ resp.formatted_content | safe }}
                        </div>
                    </div>
                </div>
            </div>
            {% endfor %}
            </div>
        </div>
        {% endfor %}
        {% if session.visible_count == 0 %}
        <div class="text-sm text-slate-500 border border-slate-200 bg-white rounded-2xl p-4">
            No messages were parsed for this session. Try `lore export --all` to rebuild the index.
        </div>
        {% endif %}
    </div>
    </div>
</section>

<!-- Resume session modal -->
<div id="resume-modal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm hidden" aria-modal="true" role="dialog" aria-labelledby="resume-modal-title">
    <div class="bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 w-full max-w-lg mx-4 p-6">
        <div class="flex items-start justify-between mb-4">
            <h2 id="resume-modal-title" class="text-sm font-semibold text-slate-800 dark:text-slate-100">Resume Session</h2>
            <button onclick="closeResumeModal()" class="text-slate-500 hover:text-slate-700 dark:hover:text-slate-200 ml-4" aria-label="Close">&times;</button>
        </div>
        <div id="resume-modal-body" class="text-sm text-slate-600 dark:text-slate-300"></div>
    </div>
</div>

<script nonce="{{ nonce }}">
let resumeTrapRelease = null;
function resumeSession(sessionId) {
    const modal = document.getElementById('resume-modal');
    const body = document.getElementById('resume-modal-body');
    body.innerHTML = '<span class="text-slate-500">Loading&hellip;</span>';
    modal.classList.remove('hidden');
    const dialog = modal.firstElementChild || modal;
    if (resumeTrapRelease) { resumeTrapRelease(); resumeTrapRelease = null; }
    if (window.FocusTrap) {
        resumeTrapRelease = window.FocusTrap.activate(dialog);
    }

    fetch('/api/sessions/' + encodeURIComponent(sessionId) + '/resume', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
    })
    .then(function(res) { return res.json(); })
    .then(function(data) {
        if (data.error) {
            body.innerHTML = '<p class="text-red-600">' + escHtml(data.error) + '</p>';
            return;
        }
        if (!data.supported) {
            body.innerHTML =
                '<p class="text-amber-600 mb-2">' + escHtml(data.reason || 'Resume not supported for this tool.') + '</p>' +
                (data.tool ? '<p class="text-xs text-slate-500">Tool: ' + escHtml(data.tool) + '</p>' : '');
            return;
        }
        body.innerHTML =
            '<p class="text-slate-500 text-xs mb-2">Run this command in your terminal:</p>' +
            '<div class="relative group">' +
              '<pre class="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-3 text-xs font-mono text-slate-800 dark:text-slate-100 overflow-x-auto whitespace-pre-wrap break-all" id="resume-cmd-text">' + escHtml(data.command) + '</pre>' +
              '<button onclick="copyResumeCmd()" class="absolute top-2 right-2 text-[10px] text-slate-500 hover:text-slate-700 border border-slate-200 bg-white rounded-lg px-2 py-1 opacity-0 group-hover:opacity-100 transition-opacity" id="resume-copy-btn">Copy</button>' +
            '</div>';
    })
    .catch(function(err) {
        body.innerHTML = '<p class="text-red-600">Request failed: ' + escHtml(String(err)) + '</p>';
    });
}

function closeResumeModal() {
    const modal = document.getElementById('resume-modal');
    if (!modal || modal.classList.contains('hidden')) return;
    modal.classList.add('hidden');
    if (resumeTrapRelease) { resumeTrapRelease(); resumeTrapRelease = null; }
}

function copyResumeCmd() {
    const text = document.getElementById('resume-cmd-text').textContent || '';
    navigator.clipboard.writeText(text.trim()).then(function() {
        const btn = document.getElementById('resume-copy-btn');
        btn.textContent = 'Copied!';
        setTimeout(function() { btn.textContent = 'Copy'; }, 1500);
    });
}

function escHtml(str) {
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

document.getElementById('resume-modal').addEventListener('click', function(e) {
    if (e.target === this) { closeResumeModal(); }
});
document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') { closeResumeModal(); }
});
</script>
{% endblock %}
"""

# --- Simplified Dashboard and List ---
DASHBOARD_TEMPLATE = """
{# TODO(perf): Load summary stats from GET /api/v1/index/summary first (fast, no session data),
   then populate the Recent Activity list lazily via GET /api/v1/sessions?page=1&per_page=10.
   This avoids shipping the full index.json (can be 19MB+) on the initial page load.
   Wire up with fetch() on DOMContentLoaded and replace the static Jinja blocks below. #}
{% extends "base" %}
{% block content %}
<section class="max-w-6xl mx-auto px-8 py-10">
    <div class="flex flex-wrap items-center justify-between gap-6 mb-10">
        <div>
            <div class="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">Workspace</div>
            <h1 class="title-font page-headline text-slate-900 mt-2">Overview</h1>
            <p class="text-sm text-slate-500 mt-2">All sessions, tools, and projects in one place.</p>
        </div>
        <div class="flex items-center gap-2">
            <a href="/export/index" class="text-[11px] text-slate-500 hover:text-slate-900 border border-slate-200 px-3 py-2 rounded-xl bg-white">Export Index</a>
            <button type="button" onclick="openSearch()" class="text-[11px] text-slate-500 hover:text-slate-900 border border-slate-200 px-3 py-2 rounded-xl bg-white">New Session</button>
        </div>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-12">
        <div class="stat-card p-6">
            <div class="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500 mb-2">Sessions</div>
            <div class="text-3xl font-semibold text-slate-900">{{ stats.total_sessions }}</div>
        </div>
        <div class="stat-card p-6">
            <div class="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500 mb-2">Messages</div>
            <div class="text-3xl font-semibold text-slate-900">{{ stats.total_messages }}</div>
        </div>
        <div class="stat-card p-6">
            <div class="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500 mb-2">Tools</div>
            <div class="text-3xl font-semibold text-slate-900">{{ stats.by_tool|length }}</div>
        </div>
        <div class="stat-card p-6">
            <div class="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500 mb-2">Projects</div>
            <div class="text-3xl font-semibold text-slate-900">{{ stats.by_project|length }}</div>
        </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-10">
        <div class="lg:col-span-2">
            <div class="flex items-center justify-between mb-5">
                <h2 class="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Recent Activity</h2>
                <a href="/sessions" class="text-xs text-slate-500 hover:text-slate-900">View all</a>
            </div>
            <div class="compact-list">
                {% for s in recent_sessions %}
                <a href="/session/{{ s.id|urlpath }}" class="compact-row flex items-center gap-3 group">
                    <div class="w-8 h-8 rounded-lg flex items-center justify-center text-sm bg-white border border-slate-200" style="color: {{ get_style(s.tool).color }}">
                        {{ get_style(s.tool).icon }}
                    </div>
                    <div class="flex-1 min-w-0">
                        <div class="compact-title text-slate-900 group-hover:text-slate-900 truncate">{{ s.display_title or s.title or 'Untitled Session' }}</div>
                        <div class="text-[10px] text-slate-500 mt-1 uppercase tracking-tight">via {{ get_style(s.tool).name }} • {{ s.created[:10] }}</div>
                    </div>
                    <div class="text-[10px] font-mono text-slate-500 bg-white border border-slate-200 px-2 py-1 rounded-full">{{ s.prompts or s.messages }} prompts</div>
                </a>
                {% else %}
                <div class="compact-row text-sm text-slate-500">No sessions yet. Run <code>lore sync --all</code> and refresh to import your AI conversations.</div>
                {% endfor %}
            </div>
        </div>
        <div>
            <h2 class="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500 mb-5">Tools</h2>
            <div class="space-y-2">
                {% for tool in all_tools %}
                {% set count = stats.by_tool.get(tool, 0) %}
                <a href="/sessions?tool={{ tool }}" class="list-row flex items-center justify-between p-3 group">
                    <div class="flex items-center gap-3">
                        <div class="w-2 h-2 rounded-full" style="background: {{ get_style(tool).color }}"></div>
                        <span class="text-sm text-slate-600 group-hover:text-slate-900">{{ get_style(tool).name }}</span>
                    </div>
                    <span class="text-[10px] font-mono text-slate-500 group-hover:text-slate-700">{{ count }}</span>
                </a>
                {% endfor %}
            </div>
        </div>
    </div>
</section>
{% endblock %}
"""

# Just the <a>...row markup, shared by the full page and the lazy-load fragment.
SESSION_ROWS_TEMPLATE = """
{% for s in sessions %}
<div class="compact-row flex items-start gap-3 group">
    <a href="/session/{{ s.id|urlpath }}?back={{ (back_to or '/sessions')|urlpath }}" class="flex items-center gap-3 flex-1">
        <div class="w-8 h-8 rounded-lg flex items-center justify-center text-sm bg-white border border-slate-200" style="color: {{ get_style(s.tool).color }}">
            {{ get_style(s.tool).icon }}
        </div>
        <div class="flex-1 min-w-0">
            <div class="compact-title text-slate-900 group-hover:text-slate-900 truncate">{{ s.display_title or s.title or s.id }}</div>
            {% if s.prompt_outline %}
            <div class="text-xs text-slate-500 mt-2">{{ s.prompt_outline }}</div>
            {% endif %}
            <div class="flex flex-wrap gap-2 mt-3 text-[10px]">
                <span class="tag-chip">via {{ get_style(s.tool).name }}</span>
                <span class="tag-chip">{{ project_label(s.project) }}</span>
                <span class="tag-chip">{{ s.prompts or s.messages }} prompts</span>
            </div>
        </div>
        <div class="text-[10px] font-mono text-slate-500 group-hover:text-slate-700">{{ s.created[:10] }}</div>
    </a>
    <form action="/session/{{ s.id|urlpath }}/delete" method="POST" onsubmit="return confirm('Delete this session?');" class="ml-2">
        <input type="hidden" name="next" value="{{ back_to or '/sessions' }}">
        <button type="submit" aria-label="Delete session {{ s.display_title or s.title or s.id }}" class="text-red-600 hover:text-red-900 border border-red-200 p-1.5 rounded-lg transition-all bg-white"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 6l12 12M18 6L6 18"/></svg></button>
    </form>
</div>
{% endfor %}
"""

SESSIONS_LIST_TEMPLATE = """
{% extends "base" %}
{% block content %}
<section class="max-w-5xl mx-auto px-8 py-10">
    <div class="flex flex-wrap justify-between items-center mb-8 gap-4">
        <div>
            <div class="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">Archive</div>
            <h1 class="title-font page-headline text-slate-900 mt-2">Sessions</h1>
            <p class="text-sm text-slate-500 mt-2">{{ total }} session{{ '' if total == 1 else 's' }}</p>
        </div>
    </div>
    <form method="get" data-autosubmit="true" class="grid grid-cols-1 lg:grid-cols-5 gap-3 mb-8">
        <select name="tool" onchange="this.form.submit()" class="bg-white border border-slate-200 text-[11px] text-slate-600 rounded-xl px-3 py-2 uppercase tracking-widest font-semibold outline-none focus:border-slate-300 transition-all">
            <option value="">All Tools</option>
            {% for t in tools %}<option value="{{ t }}" {{ 'selected' if tool==t else '' }}>{{ get_style(t).name }}</option>{% endfor %}
        </select>
        <select name="tag" onchange="this.form.submit()" class="bg-white border border-slate-200 text-[11px] text-slate-600 rounded-xl px-3 py-2 uppercase tracking-widest font-semibold outline-none focus:border-slate-300 transition-all">
            <option value="">All Tags</option>
            {% for t in tags %}<option value="{{ t }}" {{ 'selected' if tag==t else '' }}>{{ t }}</option>{% endfor %}
        </select>
        <input type="date" name="start" onchange="this.form.submit()" value="{{ start or '' }}" class="bg-white border border-slate-200 text-[11px] text-slate-600 rounded-xl px-3 py-2 uppercase tracking-widest font-semibold outline-none focus:border-slate-300 transition-all">
        <input type="date" name="end" onchange="this.form.submit()" value="{{ end or '' }}" class="bg-white border border-slate-200 text-[11px] text-slate-600 rounded-xl px-3 py-2 uppercase tracking-widest font-semibold outline-none focus:border-slate-300 transition-all">
        <button type="submit" class="bg-white border border-slate-200 text-[11px] text-slate-600 rounded-xl px-3 py-2 uppercase tracking-widest font-semibold hover:text-slate-900 transition-all">Apply</button>
    </form>
    <div class="compact-list" id="sessionRows"
         data-tool="{{ tool }}" data-tag="{{ tag }}" data-start="{{ start or '' }}"
         data-end="{{ end or '' }}" data-back="{{ back_to or '/sessions' }}"
         data-per-page="{{ per_page }}" data-pages="{{ pages }}">
        {% include "session_rows" %}
    </div>
    {% if pages > 1 %}
    <div class="flex justify-center mt-8">
        <button type="button" id="loadMoreSessions" data-next-page="2"
                class="bg-white border border-slate-200 text-[11px] text-slate-600 rounded-xl px-5 py-2.5 uppercase tracking-widest font-semibold hover:text-slate-900 transition-all">
            Load more
        </button>
    </div>
    {% endif %}
</section>
<script nonce="{{ nonce }}">
(function () {
    const btn = document.getElementById('loadMoreSessions');
    const rows = document.getElementById('sessionRows');
    if (!btn || !rows) return;
    const totalPages = parseInt(rows.dataset.pages || '1', 10);
    btn.addEventListener('click', async function () {
        const page = parseInt(btn.dataset.nextPage || '2', 10);
        btn.disabled = true;
        btn.textContent = 'Loading…';
        const params = new URLSearchParams({
            page: String(page),
            tool: rows.dataset.tool || '',
            tag: rows.dataset.tag || '',
            start: rows.dataset.start || '',
            end: rows.dataset.end || '',
        });
        try {
            const resp = await fetch('/sessions/rows?' + params.toString(), { credentials: 'same-origin' });
            if (!resp.ok) throw new Error('HTTP ' + resp.status);
            const html = await resp.text();
            rows.insertAdjacentHTML('beforeend', html);
            if (page + 1 > totalPages) {
                btn.remove();
            } else {
                btn.dataset.nextPage = String(page + 1);
                btn.disabled = false;
                btn.textContent = 'Load more';
            }
        } catch (err) {
            btn.disabled = false;
            btn.textContent = 'Load more (retry)';
        }
    });
})();
</script>
{% endblock %}
"""

RULES_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div class="p-10 max-w-4xl mx-auto">
    <h1 class="text-3xl font-bold text-slate-900 mb-6 tracking-tight">Rules</h1>
    <div class="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
        <p class="text-xs text-slate-500 mb-4">Rules are project-level instruction files and operating guidelines collected from your workspace (for example AGENTS.md / CLAUDE.md style docs).</p>
        {% if rules %}
        <div class="prose max-w-none antialiased">{{ rules | safe }}</div>
        {% else %}
        <div class="text-sm text-slate-500">No rules yet. Run `lore rules --rebuild` to generate.</div>
        {% endif %}
    </div>
</div>
{% endblock %}
"""

MEMORY_TEMPLATE = """
{% extends "base" %}
{% block content %}
<section class="max-w-4xl mx-auto px-8 py-10">
    <div class="flex flex-wrap items-center justify-between gap-4 mb-8">
        <div>
            <div class="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">Knowledge</div>
            <h1 class="title-font page-headline text-slate-900 mt-2">Memory</h1>
            <p class="text-sm text-slate-500 mt-2">
                {{ total }} entr{{ 'y' if total == 1 else 'ies' }} — facts, decisions and lessons
                any AI tool can record and recall.
            </p>
        </div>
    </div>

    <form method="get" class="flex flex-wrap items-center gap-3 mb-8">
        <input type="text" name="q" value="{{ query or '' }}"
               placeholder="Search memory…" aria-label="Search memory"
               class="flex-1 min-w-[12rem] bg-white border border-slate-200 text-sm text-slate-700 rounded-xl px-3 py-2 outline-none focus:border-slate-300">
        <select name="kind" aria-label="Filter by kind"
                class="bg-white border border-slate-200 text-[11px] text-slate-600 rounded-xl px-3 py-2 uppercase tracking-widest font-semibold outline-none focus:border-slate-300">
            <option value="">All kinds</option>
            {% for k in kinds %}<option value="{{ k }}" {{ 'selected' if kind==k else '' }}>{{ k }}</option>{% endfor %}
        </select>
        <label class="flex items-center gap-2 text-[11px] text-slate-600 uppercase tracking-widest font-semibold">
            <input type="checkbox" name="semantic" value="1" {{ 'checked' if semantic else '' }} class="w-4 h-4">
            Semantic
        </label>
        <button type="submit"
                class="bg-white border border-slate-200 text-[11px] text-slate-600 rounded-xl px-4 py-2 uppercase tracking-widest font-semibold hover:text-slate-900 transition-all">
            Search
        </button>
    </form>

    {% if semantic and not semantic_available %}
    <div class="text-[11px] text-amber-700 bg-amber-50 border border-amber-200 rounded-xl px-3 py-2 mb-6">
        Semantic search needs the optional embedding model
        (<span class="font-mono">pip install -e ".[semantic]"</span>) — showing keyword results instead.
    </div>
    {% endif %}

    <div class="space-y-3">
        {% for m in memories %}
        <article class="surface-card p-5">
            <div class="flex items-start justify-between gap-3">
                <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-2 mb-1">
                        <span class="tag-chip uppercase">{{ m.kind }}</span>
                        {% if m.scope_project %}<span class="tag-chip">{{ project_label(m.scope_project) }}</span>{% endif %}
                        {% if m.scope_tool %}<span class="tag-chip">{{ m.scope_tool }}</span>{% endif %}
                    </div>
                    {# SECURITY (#43): memory is agent-writable — title/body
                       MUST stay {{ }}-escaped. Never switch these to | safe
                       without routing through nh3 sanitisation first. #}
                    <h2 class="text-sm font-semibold text-slate-900">{{ m.title }}</h2>
                    <p class="text-sm text-slate-600 mt-1.5 whitespace-pre-wrap">{{ m.body }}</p>
                    <div class="flex flex-wrap gap-1.5 mt-3">
                        {% for tag in m.tags %}<span class="tag-chip text-[10px]">#{{ tag }}</span>{% endfor %}
                    </div>
                </div>
                <form action="/memory/{{ m.id }}/delete" method="POST"
                      onsubmit="return confirm('Delete this memory?');">
                    <button type="submit" aria-label="Delete memory {{ m.title }}"
                            class="text-[10px] text-red-600 hover:text-red-900 border border-red-200 px-2 py-1 rounded-lg bg-white transition-all">
                        <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                             stroke-width="2.5" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>
                    </button>
                </form>
            </div>
            <div class="text-[10px] text-slate-500 mt-3 uppercase tracking-tight">
                {{ m.author or 'unknown' }} · {{ m.created[:10] }}
            </div>
            {% if m.sources %}
            <div class="text-[10px] text-slate-500 mt-2 flex flex-wrap gap-1.5 items-center">
                <span class="uppercase tracking-tight">From:</span>
                {% for src in m.sources %}
                <a href="/session/{{ src.session_id|urlpath }}" class="tag-chip hover:text-slate-900"
                   title="Session this memory was recorded from">{{ src.session_id[:16] }}</a>
                {% endfor %}
            </div>
            {% endif %}
        </article>
        {% else %}
        <div class="surface-card p-8 text-center">
            <p class="text-sm text-slate-600">No memory entries{{ ' match your search' if query else ' yet' }}.</p>
            <p class="text-xs text-slate-500 mt-2">
                Record one with <span class="font-mono">lore memory add</span>, or let an
                AI agent write to it via the <span class="font-mono">memory_write</span> MCP tool.
            </p>
        </div>
        {% endfor %}
    </div>
</section>
{% endblock %}
"""

NOISE_RULES_TEMPLATE = """
{% extends "base" %}
{% block content %}
<section class="max-w-4xl mx-auto px-8 py-10">
    <div class="surface-card p-6">
        <div class="flex items-center justify-between gap-4 mb-6">
            <div>
                <div class="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">Readability</div>
                <h1 class="title-font page-headline text-slate-900 mt-2">Noise Rules</h1>
                <p class="text-sm text-slate-500 mt-2">Configure provider-specific cleanup rules for session rendering.</p>
            </div>
            <div class="flex items-center gap-2">
                <button type="button" id="noiseRulesResetBtn" class="density-toggle border">Reset to Saved</button>
                <button type="button" id="noiseRulesSaveBtn" class="density-toggle border">Save</button>
            </div>
        </div>

        <div class="list-row p-4 mb-4">
            <div class="text-xs font-semibold text-slate-900 mb-3">Presets</div>
            <div class="flex flex-wrap gap-2" id="noisePresetBar">
                {% for preset_key, preset in noise_rule_presets.items() %}
                <button
                    type="button"
                    class="density-toggle border"
                    data-preset="{{ preset_key }}"
                    title="{{ preset.description }}"
                >{{ preset.label }}</button>
                {% endfor %}
            </div>
        </div>

        <div class="space-y-4" id="noiseRulesForm">
            {% for provider, rules in noise_rules.items() %}
            <div class="list-row p-4">
                <div class="text-xs font-semibold text-slate-900 mb-3">{{ get_style(provider).name if provider in provider_tools else provider }}</div>
                <div class="space-y-2">
                    {% for key, value in rules.items() %}
                    <label class="flex items-center justify-between gap-4 text-sm text-slate-600">
                        <span class="font-mono text-[12px]">{{ key }}</span>
                        <input
                            type="checkbox"
                            data-provider="{{ provider }}"
                            data-key="{{ key }}"
                            {% if value %}checked{% endif %}
                            class="w-4 h-4"
                        >
                    </label>
                    {% endfor %}
                </div>
            </div>
            {% endfor %}
        </div>

        <div class="mt-8 list-row p-4" id="noiseRulesPreview">
            <div class="text-xs font-semibold text-slate-900 mb-3">Preview (before save)</div>
            <div class="grid grid-cols-1 md:grid-cols-2 gap-3 mb-3">
                <select id="noisePreviewProvider" class="bg-white border border-slate-200 text-[11px] text-slate-600 rounded-xl px-3 py-2 uppercase tracking-widest font-semibold outline-none focus:border-slate-300 transition-all">
                    {% for provider in provider_tools %}
                    <option value="{{ provider }}">{{ get_style(provider).name }}</option>
                    {% endfor %}
                </select>
                <select id="noisePreviewRole" class="bg-white border border-slate-200 text-[11px] text-slate-600 rounded-xl px-3 py-2 uppercase tracking-widest font-semibold outline-none focus:border-slate-300 transition-all">
                    <option value="assistant">assistant</option>
                    <option value="user">user</option>
                </select>
            </div>
            <textarea id="noisePreviewInput" class="w-full min-h-[140px] bg-white border border-slate-200 rounded-xl p-3 text-sm font-mono text-slate-700" placeholder="Paste a noisy message here..."></textarea>
            <div class="flex items-center gap-2 mt-3">
                <button type="button" id="noiseRulesPreviewBtn" class="density-toggle border">Preview</button>
                <span class="text-xs text-slate-500">Uses your current checkbox state, even before Save.</span>
            </div>
            <pre id="noisePreviewOutput" class="mt-3 bg-slate-50 border border-slate-200 rounded-xl p-3 text-sm text-slate-700 whitespace-pre-wrap"></pre>
        </div>
    </div>
</section>
<script nonce="{{ nonce }}">
    document.addEventListener('DOMContentLoaded', () => {
        const saveBtn = document.getElementById('noiseRulesSaveBtn');
        const resetBtn = document.getElementById('noiseRulesResetBtn');
        const previewBtn = document.getElementById('noiseRulesPreviewBtn');
        const presetBar = document.getElementById('noisePresetBar');
        const presets = {{ noise_rule_presets | tojson | safe }};

        function collectRulesPayload() {
            const inputs = Array.from(document.querySelectorAll('#noiseRulesForm input[type="checkbox"]'));
            const payload = {};
            for (const input of inputs) {
                const provider = String(input.getAttribute('data-provider') || '').trim();
                const key = String(input.getAttribute('data-key') || '').trim();
                if (!provider || !key) continue;
                if (!payload[provider]) payload[provider] = {};
                payload[provider][key] = Boolean(input.checked);
            }
            return payload;
        }

        function applyRulesToInputs(rulesPayload) {
            const rules = (rulesPayload && typeof rulesPayload === 'object') ? rulesPayload : {};
            const inputs = Array.from(document.querySelectorAll('#noiseRulesForm input[type="checkbox"]'));
            for (const input of inputs) {
                const provider = String(input.getAttribute('data-provider') || '').trim();
                const key = String(input.getAttribute('data-key') || '').trim();
                if (!provider || !key) continue;
                const providerRules = (rules[provider] && typeof rules[provider] === 'object') ? rules[provider] : {};
                if (Object.prototype.hasOwnProperty.call(providerRules, key)) {
                    input.checked = Boolean(providerRules[key]);
                }
            }
        }

        function applyPreset(presetKey) {
            const preset = presets[presetKey];
            if (!preset || !preset.rules) return;
            const inputs = Array.from(document.querySelectorAll('#noiseRulesForm input[type="checkbox"]'));
            for (const input of inputs) {
                const provider = String(input.getAttribute('data-provider') || '').trim();
                const key = String(input.getAttribute('data-key') || '').trim();
                const providerRules = (preset.rules[provider] || {});
                if (Object.prototype.hasOwnProperty.call(providerRules, key)) {
                    input.checked = Boolean(providerRules[key]);
                }
            }
        }

        if (presetBar) {
            presetBar.addEventListener('click', (event) => {
                const target = event.target;
                if (!(target instanceof HTMLElement)) return;
                const presetKey = String(target.getAttribute('data-preset') || '').trim();
                if (!presetKey) return;
                applyPreset(presetKey);
            });
        }

        if (saveBtn) {
            saveBtn.addEventListener('click', async () => {
                const payload = collectRulesPayload();

                const original = saveBtn.textContent;
                saveBtn.disabled = true;
                saveBtn.textContent = 'Saving...';
                try {
                    const response = await fetch('/api/noise-rules', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'same-origin',
                        body: JSON.stringify(payload),
                    });
                    const data = await response.json();
                    if (!response.ok) throw new Error(data.error || 'Save failed');
                    saveBtn.textContent = 'Saved';
                    setTimeout(() => { saveBtn.textContent = original || 'Save'; }, 1200);
                } catch (error) {
                    saveBtn.textContent = 'Save failed';
                    setTimeout(() => { saveBtn.textContent = original || 'Save'; }, 1800);
                } finally {
                    saveBtn.disabled = false;
                }
            });
        }

        if (resetBtn) {
            resetBtn.addEventListener('click', async () => {
                const original = resetBtn.textContent;
                resetBtn.disabled = true;
                resetBtn.textContent = 'Resetting...';
                try {
                    const response = await fetch('/api/noise-rules', {
                        method: 'GET',
                        credentials: 'same-origin',
                    });
                    const data = await response.json();
                    if (!response.ok) throw new Error(data.error || 'Reset failed');
                    applyRulesToInputs(data);
                    resetBtn.textContent = 'Reset';
                    setTimeout(() => { resetBtn.textContent = original || 'Reset to Saved'; }, 900);
                } catch (error) {
                    resetBtn.textContent = 'Reset failed';
                    setTimeout(() => { resetBtn.textContent = original || 'Reset to Saved'; }, 1500);
                } finally {
                    resetBtn.disabled = false;
                }
            });
        }

        if (previewBtn) {
            previewBtn.addEventListener('click', async () => {
                const provider = String(document.getElementById('noisePreviewProvider')?.value || '').trim();
                const role = String(document.getElementById('noisePreviewRole')?.value || 'assistant').trim();
                const content = String(document.getElementById('noisePreviewInput')?.value || '');
                const output = document.getElementById('noisePreviewOutput');
                const payload = {
                    tool: provider,
                    role,
                    content,
                    noise_rules: collectRulesPayload(),
                };

                const original = previewBtn.textContent;
                previewBtn.disabled = true;
                previewBtn.textContent = 'Rendering...';
                if (output) output.textContent = '';
                try {
                    const response = await fetch('/api/noise-rules/preview', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        credentials: 'same-origin',
                        body: JSON.stringify(payload),
                    });
                    const data = await response.json();
                    if (!response.ok) throw new Error(data.error || 'Preview failed');
                    if (output) output.textContent = String(data.content || '');
                } catch (error) {
                    if (output) output.textContent = `Preview failed: ${error.message}`;
                } finally {
                    previewBtn.disabled = false;
                    previewBtn.textContent = original || 'Preview';
                }
            });
        }
    });
</script>
{% endblock %}
"""
THREADS_LIST_TEMPLATE = """
{% extends "base" %}
{% block content %}
<section class="max-w-5xl mx-auto px-8 py-10">
    <div class="flex justify-between items-center mb-8">
        <div>
            <div class="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">Connections</div>
            <h1 class="title-font page-headline text-slate-900 mt-2">Threads</h1>
        </div>
    </div>
    <div class="compact-list">
        {% for t in threads %}
        <a href="/thread/{{ t.thread_id|urlpath }}" class="compact-row flex items-center gap-3 group">
            <div class="w-8 h-8 rounded-lg flex items-center justify-center text-sm bg-white border border-slate-200 text-slate-500">T</div>
            <div class="flex-1 min-w-0">
                <div class="compact-title text-slate-900 group-hover:text-slate-900 truncate">{{ t.title }}</div>
                <div class="text-[10px] text-slate-500 mt-1 truncate uppercase tracking-[0.2em]">{{ t.project or 'No Project' }}</div>
            </div>
            <div class="text-[10px] font-mono text-slate-500 group-hover:text-slate-700">{{ t.count }} sessions</div>
        </a>
        {% endfor %}
        {% if threads|length == 0 %}
        <div class="compact-row text-sm text-slate-500">No thread groups found yet. Run <code>lore sync --all</code> and refresh to build cross-session thread continuity.</div>
        {% endif %}
    </div>
</section>
{% endblock %}
"""

PROJECTS_TEMPLATE = """
{% extends "base" %}
{% block content %}
<section class="max-w-6xl mx-auto px-8 py-10">
    <div class="flex flex-wrap justify-between items-center mb-8 gap-4">
        <div>
            <div class="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">Workspace</div>
            <h1 class="title-font page-headline text-slate-900 mt-2">Projects</h1>
        </div>
    </div>
    <form method="get" data-autosubmit="true" class="grid grid-cols-1 lg:grid-cols-5 gap-3 mb-8">
        <select name="tool" onchange="this.form.submit()" class="bg-white border border-slate-200 text-[11px] text-slate-600 rounded-xl px-3 py-2 uppercase tracking-widest font-semibold outline-none focus:border-slate-300 transition-all">
            <option value="">All Tools</option>
            {% for t in tools %}<option value="{{ t }}" {{ 'selected' if tool==t else '' }}>{{ get_style(t).name }}</option>{% endfor %}
        </select>
        <select name="tag" onchange="this.form.submit()" class="bg-white border border-slate-200 text-[11px] text-slate-600 rounded-xl px-3 py-2 uppercase tracking-widest font-semibold outline-none focus:border-slate-300 transition-all">
            <option value="">All Tags</option>
            {% for t in tags %}<option value="{{ t }}" {{ 'selected' if tag==t else '' }}>{{ t }}</option>{% endfor %}
        </select>
        <input type="date" name="start" onchange="this.form.submit()" value="{{ start or '' }}" class="bg-white border border-slate-200 text-[11px] text-slate-600 rounded-xl px-3 py-2 uppercase tracking-widest font-semibold outline-none focus:border-slate-300 transition-all">
        <input type="date" name="end" onchange="this.form.submit()" value="{{ end or '' }}" class="bg-white border border-slate-200 text-[11px] text-slate-600 rounded-xl px-3 py-2 uppercase tracking-widest font-semibold outline-none focus:border-slate-300 transition-all">
        <button type="submit" class="bg-white border border-slate-200 text-[11px] text-slate-600 rounded-xl px-3 py-2 uppercase tracking-widest font-semibold hover:text-slate-900 transition-all">Apply</button>
    </form>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {% for p in projects %}
        <div class="surface-card p-5">
            <div class="flex items-start justify-between gap-4">
                <div>
                    <div class="text-xs font-semibold text-slate-900">{{ p.name }}</div>
                    <div class="text-[10px] text-slate-500 mt-1">{{ p.path }}</div>
                </div>
                <div class="text-[10px] text-slate-500 font-mono">{{ p.updated }}</div>
            </div>
            <div class="flex flex-wrap gap-2 mt-4 text-[10px]">
                <span class="tag-chip">{{ p.session_count }} sessions</span>
                <span class="tag-chip">{{ p.prompt_count }} prompts</span>
                {% for tool, count in p.tool_counts.items() %}
                <span class="tag-chip">via {{ get_style(tool).name }} · {{ count }}</span>
                {% endfor %}
            </div>
            {% if p.agents %}
            <div class="flex items-center gap-2 mt-4">
                {% for agent in p.agents %}
                <div class="w-9 h-9 rounded-xl border border-slate-200 bg-white flex items-center justify-center text-xs font-semibold" style="color: {{ get_style(agent.tool).color }}" title="{{ get_style(agent.tool).name }} · {{ agent.count }}">
                    {{ get_style(agent.tool).icon }}
                </div>
                {% endfor %}
            </div>
            {% endif %}
            <div class="mt-4 space-y-3">
                {% for s in p.recent_sessions %}
                <a href="/session/{{ s.id|urlpath }}" class="list-row block p-3 transition-all">
                    <div class="text-sm font-semibold text-slate-900 truncate">{{ s.display_title or s.title or s.id }}</div>
                    {% if s.prompt_outline %}
                    <div class="text-xs text-slate-500 mt-1">{{ s.prompt_outline }}</div>
                    {% endif %}
                    <div class="text-[10px] text-slate-500 mt-2">via {{ get_style(s.tool).name }} • {{ s.prompts or s.messages }} prompts • {{ s.created[:10] }}</div>
                </a>
                {% endfor %}
            </div>
        </div>
        {% else %}
        <div class="compact-row text-sm text-slate-500 lg:col-span-2">No projects found. Run <code>lore sync --all</code> and refresh to group your sessions by project.</div>
        {% endfor %}
    </div>
</section>
{% endblock %}
"""

THREAD_DETAIL_TEMPLATE = """
{% extends "base" %}
{% block content %}
<div data-transcript-view="1" hidden></div>
<section class="max-w-[90rem] mx-auto px-6 pt-6 pb-4">
    <div class="surface-card flex flex-wrap items-center justify-between gap-4 px-5 py-4 backdrop-blur-xl">
        <div class="min-w-0">
            <h1 class="session-headline truncate">Thread {{ thread_id[-10:] }}</h1>
            <div class="session-meta mt-2">
                <span>Thread timeline</span>
                <span class="session-meta-dot"></span>
                <span>{{ thread_meta.session_count }} sessions</span>
                <span class="session-meta-dot"></span>
                <span>{{ thread_meta.message_count }} messages</span>
            </div>
            <div class="flex flex-wrap gap-2 mt-3">
                <span class="pill bg-white border border-slate-200 text-slate-500 font-mono">{{ thread_id }}</span>
            </div>
        </div>
        <div class="flex flex-wrap items-center gap-2">
                <button onclick='copyCommand({{ continue_cmd|tojson }})' class="text-[11px] text-slate-500 hover:text-slate-900 border border-slate-200 px-3 py-1.5 rounded-xl transition-all bg-white">Copy Continue</button>
            <a href="/threads" class="text-[11px] text-slate-500 hover:text-slate-900 border border-slate-200 px-3 py-1.5 rounded-xl transition-all bg-white">All Threads</a>
        </div>
    </div>
</section>

<section class="max-w-[90rem] mx-auto px-6 pb-24">
    <div class="flex flex-col lg:flex-row w-full">
    <aside class="hidden lg:block lg:flex-grow lg:flex-shrink-[100] lg:basis-[550px] lg:min-w-[350px] lg:max-w-[550px] lg:pr-6">
        <div class="toc-card sticky top-24 h-[calc(100vh-12rem)]">
            <div class="toc-card-head">On this page</div>
            <nav aria-label="Table of contents">
            <ol class="toc-stepper toc-list space-y-0.5">
                {% for item in toc_items %}
                <li>
                <a href="#tmsg-{{ item.index }}" class="toc-item" data-toc="tmsg-{{ item.index }}" title="{{ item.text }}">
                    <span class="toc-badge">{{ loop.index }}</span>
                    <span class="toc-item-text">{{ item.text }}</span>
                    <span class="toc-item-meta">{{ item.time }}</span>
                </a>
                </li>
                {% endfor %}
                {% if toc_items|length == 0 %}
                <li class="text-[11px] text-slate-500 px-3 py-2">No prompts detected.</li>
                {% endif %}
            </ol>
            </nav>
            <div class="toc-card-foot">{{ toc_items|length }} entries</div>
        </div>
    </aside>
    <div class="lg:flex-grow-0 lg:flex-shrink-1 lg:basis-[850px] lg:min-w-[500px] lg:px-8 space-y-6">
        <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
            <div class="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500 mb-3">Continuation Cluster</div>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
                {% for group in thread_groups %}
                <div class="border border-slate-200 rounded-xl p-3">
                    <div class="flex items-center justify-between">
                        <div class="text-xs font-semibold text-slate-900">via {{ get_style(group.tool).name }}</div>
                        <span class="text-[10px] text-slate-500 font-mono">{{ group.count }}</span>
                    </div>
                    <div class="mt-3 space-y-2">
                        {% for s in group.sessions %}
                        <a href="/session/{{ s.id|urlpath }}" class="block text-xs text-slate-600 hover:text-slate-900">
                    <div class="font-semibold truncate">{{ s.display_title or s.title or s.id }}</div>
                            <div class="text-[10px] text-slate-500">{{ s.prompts or s.messages }} prompts • {{ s.created[:10] }}</div>
                        </a>
                        {% endfor %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
            <div class="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500 mb-3">Timeline</div>
            <div class="space-y-3">
                {% for s in thread_timeline %}
                <a href="/session/{{ s.id|urlpath }}" class="flex items-center gap-3 p-3 rounded-xl border border-slate-200 hover:bg-slate-50 transition-all">
                    <div class="w-2 h-2 rounded-full" style="background: {{ get_style(s.tool).color }}"></div>
                    <div class="flex-1 min-w-0">
                    <div class="text-sm font-semibold text-slate-900 truncate">{{ s.display_title or s.title or s.id }}</div>
                        <div class="text-[10px] text-slate-500">via {{ get_style(s.tool).name }} • {{ s.prompts or s.messages }} prompts</div>
                    </div>
                    <div class="text-[10px] text-slate-500 font-mono">{{ s.created[:10] }}</div>
                </a>
                {% endfor %}
            </div>
        </div>
        <div class="bg-white border border-slate-200 rounded-2xl p-5 shadow-sm">
            <div class="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500 mb-2">Thread Summary</div>
            <div class="flex flex-wrap gap-3 text-xs text-slate-600">
                <span class="px-2 py-1 rounded-full border border-slate-200 bg-white">Sessions: {{ thread_meta.session_count }}</span>
                <span class="px-2 py-1 rounded-full border border-slate-200 bg-white">Messages: {{ thread_meta.message_count }}</span>
                <span class="px-2 py-1 rounded-full border border-slate-200 bg-white">Tools: {{ thread_meta.tools }}</span>
                <span class="px-2 py-1 rounded-full border border-slate-200 bg-white">Start: {{ thread_meta.start_date }}</span>
                <span class="px-2 py-1 rounded-full border border-slate-200 bg-white">Last: {{ thread_meta.end_date }}</span>
            </div>
        </div>
        {% for msg in messages %}
        <div id="tmsg-{{ loop.index0 }}" class="flex gap-3 items-start group">
            <div class="flex-shrink-0 w-10 h-10 rounded-2xl border border-slate-200 bg-white flex items-center justify-center text-xs font-semibold text-slate-500">
                {% if msg.role.value == 'user' %}
                You
                {% else %}
                {{ msg.style.icon }}
                {% endif %}
            </div>
            <div class="flex-1 min-w-0 max-w-3xl">
                <div class="flex items-center justify-between mb-2">
                    <div class="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500">{{ msg.label }}</div>
                    <div class="text-[10px] text-slate-500 font-mono opacity-60">{{ msg.timestamp.strftime('%H:%M') }}</div>
                </div>
        <div class="message-card p-4 {% if msg.role.value == 'user' %}user-card{% else %}assistant-card{% endif %}">
                    <div class="prose max-w-none antialiased">
                        {{ msg.content | safe }}
                    </div>
                </div>
            </div>
        </div>
        {% endfor %}
    </div>
    </div>
</section>
{% endblock %}
"""

STATS_TEMPLATE = """
{% extends "base" %}
{% block content %}
<section class="max-w-6xl mx-auto px-8 py-10">
    <div class="flex flex-wrap items-center justify-between gap-6 mb-10">
        <div>
            <div class="text-[10px] font-semibold uppercase tracking-[0.24em] text-slate-500">Usage</div>
            <h1 class="title-font page-headline text-slate-900 mt-2">Token Cost Dashboard</h1>
            <p class="text-sm text-slate-500 mt-2">Estimated token usage across all AI tools. Blended rate: $3 / 1M tokens.</p>
        </div>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-12">
        <div class="stat-card p-6">
            <div class="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500 mb-2">Total Tokens</div>
            <div class="text-3xl font-semibold text-slate-900">{{ "{:,}".format(total_tokens) }}</div>
        </div>
        <div class="stat-card p-6">
            <div class="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500 mb-2">Est. Cost (USD)</div>
            <div class="text-3xl font-semibold text-slate-900">${{ "%.2f"|format(total_tokens / 1_000_000 * 3) }}</div>
        </div>
        <div class="stat-card p-6">
            <div class="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500 mb-2">Sessions (with tokens)</div>
            <div class="text-3xl font-semibold text-slate-900">{{ "{:,}".format(session_count) }}</div>
        </div>
        <div class="stat-card p-6">
            <div class="text-[10px] font-semibold uppercase tracking-[0.2em] text-slate-500 mb-2">Avg Tokens / Session</div>
            <div class="text-3xl font-semibold text-slate-900">{{ "{:,}".format((total_tokens // session_count) if session_count else 0) }}</div>
        </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-10 mb-12">
        <div>
            <h2 class="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500 mb-5">Tokens by Tool</h2>
            <div class="surface-card p-6 space-y-4">
                {% set max_tool_tokens = by_tool[0][1] if by_tool else 1 %}
                {% for tool_name, tokens in by_tool %}
                <div>
                    <div class="flex items-center justify-between mb-1.5">
                        <div class="flex items-center gap-2">
                            <div class="w-2 h-2 rounded-full" style="background: {{ get_style(tool_name).color }}"></div>
                            <span class="text-sm text-slate-700">{{ get_style(tool_name).name }}</span>
                        </div>
                        <div class="text-right">
                            <span class="text-xs font-mono text-slate-500">{{ "{:,}".format(tokens) }}</span>
                            <span class="text-[10px] text-slate-500 ml-2">${{ "%.2f"|format(tokens / 1_000_000 * 3) }}</span>
                        </div>
                    </div>
                    <div class="h-2 bg-slate-100 rounded-full overflow-hidden">
                        <div class="h-full rounded-full transition-all" style="width: {{ [(tokens * 100 // max_tool_tokens), 100]|min }}%; background: {{ get_style(tool_name).color }}; opacity: 0.75;"></div>
                    </div>
                </div>
                {% else %}
                <div class="text-sm text-slate-500">No token data available.</div>
                {% endfor %}
            </div>
        </div>

        <div>
            <h2 class="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500 mb-5">Daily Usage — Last 30 Days</h2>
            <div class="surface-card p-6">
                {% if by_day %}
                {% set max_day = namespace(v=1) %}
                {% for day in by_day %}{% if day.tokens > max_day.v %}{% set max_day.v = day.tokens %}{% endif %}{% endfor %}
                <div class="flex items-end gap-px h-24" aria-label="Daily token usage sparkline">
                    {% for day in by_day %}
                    <div class="flex-1 flex flex-col items-center justify-end h-full group relative">
                        <div class="absolute bottom-full mb-1 hidden group-hover:block bg-slate-800 text-white text-[10px] rounded px-1.5 py-0.5 whitespace-nowrap z-10">
                            {{ day.date }}: {{ "{:,}".format(day.tokens) }}
                        </div>
                        <div class="w-full rounded-t-sm bg-blue-400 opacity-70 group-hover:opacity-100 transition-opacity"
                             style="height: {{ [(day.tokens * 100 // max_day.v), 100]|min }}%;"></div>
                    </div>
                    {% endfor %}
                </div>
                <div class="flex justify-between text-[10px] text-slate-500 mt-2">
                    <span>{{ by_day[0].date }}</span>
                    <span>{{ by_day[-1].date }}</span>
                </div>
                {% else %}
                <div class="text-sm text-slate-500">No daily data available.</div>
                {% endif %}
            </div>
        </div>
    </div>

    <div>
        <h2 class="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500 mb-5">Top 10 Projects by Token Usage</h2>
        <div class="surface-card overflow-hidden">
            <table class="w-full text-sm">
                <thead>
                    <tr class="border-b border-slate-100">
                        <th class="text-left text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500 px-6 py-3">#</th>
                        <th class="text-left text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500 px-6 py-3">Project</th>
                        <th class="text-right text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500 px-6 py-3">Tokens</th>
                        <th class="text-right text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-500 px-6 py-3">Est. Cost</th>
                    </tr>
                </thead>
                <tbody>
                    {% for proj in by_project %}
                    <tr class="border-b border-slate-50 hover:bg-slate-50 transition-colors">
                        <td class="px-6 py-3 text-[11px] font-mono text-slate-500">{{ loop.index }}</td>
                        <td class="px-6 py-3">
                            <a href="/projects" class="text-slate-700 hover:text-slate-900 font-medium truncate block max-w-md" title="{{ proj.project }}">{{ proj.project | replace('/home/', '~/') | truncate(60) }}</a>
                        </td>
                        <td class="px-6 py-3 text-right font-mono text-slate-600 text-xs">{{ "{:,}".format(proj.tokens) }}</td>
                        <td class="px-6 py-3 text-right font-mono text-slate-500 text-xs">${{ "%.2f"|format(proj.tokens / 1_000_000 * 3) }}</td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="4" class="px-6 py-6 text-sm text-slate-500 text-center">No project token data available.</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</section>
{% endblock %}
"""
