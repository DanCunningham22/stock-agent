import streamlit as st
from pathlib import Path
from datetime import date

from orchestrator import analyze_stock, run_daily_research, run_alert_scan
from tools.cache import init_cache
from tools.screener import run_full_screener, screen_stocks_simple, get_available_sectors
from config import WATCHLIST

st.set_page_config(page_title="Stock Research Agent", page_icon="📈", layout="wide")
init_cache()
Path("reports").mkdir(exist_ok=True)

# Sidebar
st.sidebar.title("Stock Research Agent")
st.sidebar.markdown("AI research + Polymarket + screener + alerts")
st.sidebar.markdown("---")
mode = st.sidebar.radio("Mode", ["Screener", "Single Stock", "Batch Analysis", "Alert Scanner", "Past Reports"])
st.sidebar.markdown("---")
st.sidebar.markdown("**Screener:** Free\n\n**Full analysis:** ~$0.15-0.20/stock\n\n**Alert scan:** Free\n\n*Not financial advice.*")


def save_report(ticker, report):
    output_dir = Path("reports")
    output_dir.mkdir(exist_ok=True)
    filepath = output_dir / f"{ticker}_{date.today()}.md"
    filepath.write_text(report, encoding="utf-8")
    return filepath


# ── Screener Mode ────────────────────────────────────────────
if mode == "Screener":
    st.title("Stock Screener")

    scan_type = st.radio(
        "Scan type",
        ["Full Market Scan (~500+ stocks, 15-25 min)", "Quick Scan (~170 stocks, 2-3 min)"],
        horizontal=True,
    )

    if scan_type.startswith("Full"):
        st.markdown("Scans S&P 500 + popular mid/small caps using 4 strategies. **Completely free.**")

        with st.expander("Strategy Settings", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                use_value = st.checkbox("Value Plays (low P/E + high analyst upside)", value=True)
                use_growth = st.checkbox("Growth Rockets (high revenue growth)", value=True)
            with col2:
                use_insider = st.checkbox("Insider Buying (executives buying stock)", value=True)
                use_bounce = st.checkbox("Bounce Candidates (near 52-week lows)", value=True)

            max_candidates = st.slider("Max candidates to return", 10, 50, 30)

        run_full = st.button("Run Full Market Scan (Free)", type="primary")

        if run_full:
            strategies = []
            if use_value:
                strategies.append("VALUE")
            if use_growth:
                strategies.append("GROWTH")
            if use_insider:
                strategies.append("INSIDER")
            if use_bounce:
                strategies.append("BOUNCE")

            if not strategies:
                st.warning("Select at least one strategy.")
            else:
                status_text = st.empty()
                progress_area = st.empty()
                log_lines = []

                def full_status(msg):
                    log_lines.append(msg)
                    # Show last 8 lines
                    progress_area.code("\n".join(log_lines[-8:]), language=None)

                full_status("Starting full market scan...")

                results = run_full_screener(
                    strategies=strategies,
                    max_candidates=max_candidates,
                    status_callback=full_status,
                )

                progress_area.empty()

                if results:
                    st.success(f"Found {len(results)} top candidates!")

                    # Highlight multi-strategy stocks
                    multi = [r for r in results if r.get("multi_strategy")]
                    if multi:
                        st.markdown("### Strongest Signals (multiple strategies)")
                        st.markdown("These stocks appeared in more than one strategy filter:")
                        for r in multi:
                            strategies_str = " + ".join(r.get("strategies", []))
                            st.markdown(f"**{r['ticker']}** ({r['name'][:30]}) - {strategies_str}: {r['strategy_reason']}")

                    st.markdown("---")
                    st.markdown("### All Candidates")

                    table_data = []
                    for r in results:
                        table_data.append({
                            "Ticker": r["ticker"],
                            "Name": r["name"][:25],
                            "Strategy": " + ".join(r.get("strategies", [r.get("strategy", "")])),
                            "Price": f"${r['price']}",
                            "Mkt Cap": r["market_cap_str"],
                            "P/E": r.get("pe_ratio") or "-",
                            "Rev Growth": f"{r['revenue_growth']}%" if r.get("revenue_growth") else "-",
                            "Upside": f"{r['upside_pct']}%" if r.get("upside_pct") else "-",
                            "Why": r.get("strategy_reason", "")[:60],
                        })

                    st.dataframe(table_data, use_container_width=True, hide_index=True)

                    # Select stocks for AI analysis
                    st.markdown("---")
                    st.markdown("### Run AI Deep Dive")
                    ticker_options = [r["ticker"] for r in results]
                    selected = st.multiselect("Select stocks for full AI analysis (~$0.20 each)", ticker_options)

                    if selected:
                        cost = len(selected) * 0.20
                        st.markdown(f"**Estimated cost:** ~${cost:.2f}")
                        run_ai = st.button(f"Analyze {len(selected)} stocks", type="primary")

                        if run_ai:
                            bar = st.progress(0)
                            status = st.empty()
                            reports = {}
                            for i, t in enumerate(selected):
                                status.markdown(f"**[{i+1}/{len(selected)}]** Analyzing {t}...")
                                try:
                                    report = analyze_stock(t)
                                    if report and report.strip():
                                        reports[t] = report
                                        save_report(t, report)
                                except Exception as e:
                                    reports[t] = f"Error: {e}"
                                bar.progress((i + 1) / len(selected))
                            status.empty()
                            bar.empty()
                            st.success(f"Analyzed {len(reports)} stocks!")
                            if reports:
                                tabs = st.tabs(list(reports.keys()))
                                for tab, (t, report) in zip(tabs, reports.items()):
                                    with tab:
                                        st.markdown(report)
                                        st.download_button(f"Download {t}", data=report,
                                                           file_name=f"{t}_{date.today()}.md",
                                                           mime="text/markdown", key=f"full_dl_{t}")
                else:
                    st.warning("No candidates found. Try enabling more strategies.")

    else:  # Quick Scan
        st.markdown("Fast scan of ~170 popular stocks with custom filters. **Free.**")

        with st.expander("Filter Settings", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                sectors = st.multiselect("Sectors (empty = all)", get_available_sectors())
                min_cap = st.selectbox("Min Market Cap",
                    [("$1B", 1e9), ("$10B", 1e10), ("$50B", 5e10), ("Any", 0)],
                    format_func=lambda x: x[0])
                max_results = st.slider("Max results", 10, 50, 25)
            with col2:
                max_pe = st.number_input("Max P/E (0 = none)", min_value=0, value=0)
                min_rev = st.number_input("Min Revenue Growth % (0 = none)", min_value=0, value=0)
            with col3:
                max_de = st.number_input("Max Debt/Equity (0 = none)", min_value=0, value=0)
                near_low = st.checkbox("Near 52-week low")
                near_high = st.checkbox("Near 52-week high")

        run_quick = st.button("Run Quick Scan (Free)", type="primary")

        if run_quick:
            status_text = st.empty()
            bar = st.progress(0)
            count = [0]
            est = len(sectors) * 40 if sectors else 170

            def quick_status(msg):
                count[0] += 1
                bar.progress(min(count[0] / (est / 5), 1.0))
                status_text.markdown(f"*{msg}*")

            results = screen_stocks_simple(
                sectors=sectors or None,
                min_market_cap=min_cap[1],
                max_pe=max_pe if max_pe > 0 else None,
                min_revenue_growth=min_rev if min_rev > 0 else None,
                max_debt_to_equity=max_de if max_de > 0 else None,
                near_52_week_low=near_low,
                near_52_week_high=near_high,
                max_results=max_results,
                status_callback=quick_status,
            )
            status_text.empty()
            bar.empty()

            if results:
                st.success(f"Found {len(results)} stocks!")
                table_data = [{
                    "Ticker": r["ticker"], "Name": r["name"][:25],
                    "Price": f"${r['price']}", "Mkt Cap": r["market_cap_str"],
                    "P/E": r.get("pe_ratio") or "-",
                    "Rev Growth": f"{r['revenue_growth']}%" if r.get("revenue_growth") else "-",
                    "Upside": f"{r['upside_pct']}%" if r.get("upside_pct") else "-",
                    "Rating": r.get("recommendation") or "-",
                } for r in results]
                st.dataframe(table_data, use_container_width=True, hide_index=True)

                st.markdown("---")
                ticker_options = [r["ticker"] for r in results]
                selected = st.multiselect("Select for AI analysis (~$0.20 each)", ticker_options)
                if selected:
                    cost = len(selected) * 0.20
                    st.markdown(f"**Estimated cost:** ~${cost:.2f}")
                    if st.button(f"Analyze {len(selected)} stocks", type="primary"):
                        bar2 = st.progress(0)
                        stat2 = st.empty()
                        reports = {}
                        for i, t in enumerate(selected):
                            stat2.markdown(f"**[{i+1}/{len(selected)}]** Analyzing {t}...")
                            try:
                                report = analyze_stock(t)
                                if report and report.strip():
                                    reports[t] = report
                                    save_report(t, report)
                            except Exception as e:
                                reports[t] = f"Error: {e}"
                            bar2.progress((i+1) / len(selected))
                        stat2.empty()
                        bar2.empty()
                        if reports:
                            tabs = st.tabs(list(reports.keys()))
                            for tab, (t, rp) in zip(tabs, reports.items()):
                                with tab:
                                    st.markdown(rp)
                                    st.download_button(f"Download {t}", data=rp,
                                        file_name=f"{t}_{date.today()}.md",
                                        mime="text/markdown", key=f"q_dl_{t}")
            else:
                st.warning("No matches. Loosen the filters.")


elif mode == "Single Stock":
    st.title("Analyze a Stock")
    st.markdown("Full AI analysis with scoring, insider activity, Polymarket signals, and macro context.")
    col1, col2 = st.columns([3, 1])
    with col1:
        ticker = st.text_input("Ticker Symbol", placeholder="e.g. AAPL, HOOD, PLTR").strip().upper()
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        run_button = st.button("Analyze", type="primary", use_container_width=True)
    if run_button and ticker:
        status_container = st.empty()
        progress_text = []
        def update_status(msg):
            progress_text.append(msg)
            status_container.code("\n".join(progress_text), language=None)
        update_status(f"Starting analysis for {ticker}...")
        try:
            report = analyze_stock(ticker, status_callback=update_status)
            if report and report.strip():
                save_report(ticker, report)
                status_container.empty()
                st.success(f"Analysis complete for {ticker}!")
                st.markdown("---")
                st.markdown(report)
                st.download_button("Download Report", data=report,
                    file_name=f"{ticker}_{date.today()}.md", mime="text/markdown")
            else:
                st.error("Empty report. Try again.")
        except Exception as e:
            st.error(f"Error: {e}")
    elif run_button:
        st.warning("Enter a ticker symbol.")


elif mode == "Batch Analysis":
    st.title("Batch Analysis")
    tickers_input = st.text_input("Tickers (comma-separated)", value=", ".join(WATCHLIST))
    if st.button("Run Batch Analysis", type="primary") and tickers_input:
        tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
        bar = st.progress(0)
        stat = st.empty()
        reports = {}
        for i, t in enumerate(tickers):
            stat.markdown(f"**[{i+1}/{len(tickers)}]** Analyzing {t}...")
            try:
                report = analyze_stock(t)
                if report and report.strip():
                    reports[t] = report
                    save_report(t, report)
            except Exception as e:
                reports[t] = f"Error: {e}"
            bar.progress((i+1) / len(tickers))
        stat.empty()
        bar.empty()
        st.success(f"Analyzed {len(reports)} stocks.")
        if reports:
            tabs = st.tabs(list(reports.keys()))
            for tab, (t, rp) in zip(tabs, reports.items()):
                with tab:
                    st.markdown(rp)
                    st.download_button(f"Download {t}", data=rp,
                        file_name=f"{t}_{date.today()}.md",
                        mime="text/markdown", key=f"batch_dl_{t}")


elif mode == "Alert Scanner":
    st.title("Alert Scanner")
    st.markdown("Quick scan for actionable signals. **Free.**")
    tickers_input = st.text_input("Tickers to scan", value=", ".join(WATCHLIST))
    if st.button("Run Alert Scan", type="primary") and tickers_input:
        tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
        stat = st.empty()
        bar = st.progress(0)
        all_alerts = []
        for i, t in enumerate(tickers):
            stat.markdown(f"Scanning **{t}**...")
            try:
                from tools.market_data import get_stock_data, get_price_history, get_insider_trades
                from tools.alerts import check_alerts
                sd = get_stock_data(t).model_dump()
                pd = get_price_history(t, "1y")
                id = get_insider_trades(t)
                alerts = check_alerts(t, sd, pd, id)
                all_alerts.extend(alerts)
            except Exception as e:
                st.warning(f"Error scanning {t}: {e}")
            bar.progress((i+1) / len(tickers))
        stat.empty()
        bar.empty()
        if all_alerts:
            high = [a for a in all_alerts if a.severity == "high"]
            med = [a for a in all_alerts if a.severity == "medium"]
            if high:
                st.error(f"**{len(high)} HIGH PRIORITY**")
                for a in high:
                    st.markdown(f"**[{a.ticker}] {a.alert_type}**: {a.message}")
            if med:
                st.warning(f"**{len(med)} MEDIUM PRIORITY**")
                for a in med:
                    st.markdown(f"**[{a.ticker}] {a.alert_type}**: {a.message}")
        else:
            st.success("All clear!")


elif mode == "Past Reports":
    st.title("Past Reports")
    reports_dir = Path("reports")
    files = sorted(reports_dir.glob("*.md"), reverse=True)
    if not files:
        st.info("No reports yet.")
    else:
        for f in files:
            parts = f.stem.split("_", 1)
            with st.expander(f"{parts[0]} - {parts[1] if len(parts) > 1 else ''}"):
                content = f.read_text(encoding="utf-8")
                st.markdown(content)
                st.download_button("Download", data=content, file_name=f.name,
                    mime="text/markdown", key=f"past_{f.name}")
