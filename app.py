import streamlit as st
from pathlib import Path
from datetime import date

from orchestrator import analyze_stock, run_daily_research, run_alert_scan
from tools.cache import init_cache
from tools.screener import screen_stocks, get_available_sectors
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
    st.markdown("Scan ~170 stocks for opportunities using free data. **No AI cost.** Then analyze the ones you like.")

    with st.expander("Filter Settings", expanded=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            sectors = st.multiselect(
                "Sectors (leave empty for all)",
                get_available_sectors(),
            )
            min_market_cap = st.selectbox(
                "Min Market Cap",
                [("$1B", 1e9), ("$10B", 1e10), ("$50B", 5e10), ("$100B", 1e11), ("Any", 0)],
                format_func=lambda x: x[0],
                index=0,
            )
            max_results = st.slider("Max results", 10, 50, 25)

        with col2:
            max_pe = st.number_input("Max P/E Ratio (0 = no filter)", min_value=0, value=0)
            max_forward_pe = st.number_input("Max Forward P/E (0 = no filter)", min_value=0, value=0)
            min_revenue_growth = st.number_input("Min Revenue Growth % (0 = no filter)", min_value=0, value=0)

        with col3:
            max_debt_equity = st.number_input("Max Debt/Equity (0 = no filter)", min_value=0, value=0)
            near_52w_low = st.checkbox("Near 52-week low (within 10%)")
            near_52w_high = st.checkbox("Near 52-week high (within 5%)")

    run_screen = st.button("Run Screener (Free)", type="primary")

    if run_screen:
        status_text = st.empty()
        progress_bar = st.progress(0)

        scan_count = [0]
        total_estimate = len(sectors) * 40 if sectors else 170

        def screen_status(msg):
            scan_count[0] += 1
            progress_bar.progress(min(scan_count[0] / (total_estimate / 5), 1.0))
            status_text.markdown(f"*{msg}*")

        results = screen_stocks(
            sectors=sectors if sectors else None,
            min_market_cap=min_market_cap[1],
            max_pe=max_pe if max_pe > 0 else None,
            max_forward_pe=max_forward_pe if max_forward_pe > 0 else None,
            min_revenue_growth=min_revenue_growth if min_revenue_growth > 0 else None,
            max_debt_to_equity=max_debt_equity if max_debt_equity > 0 else None,
            near_52_week_low=near_52w_low,
            near_52_week_high=near_52w_high,
            max_results=max_results,
            status_callback=screen_status,
        )

        status_text.empty()
        progress_bar.empty()

        if results:
            st.success(f"Found {len(results)} stocks matching your criteria!")
            st.markdown("---")

            table_data = []
            for r in results:
                row = {
                    "Ticker": r["ticker"],
                    "Name": r["name"][:25],
                    "Sector": r["sector"],
                    "Price": f"${r['price']}",
                    "Mkt Cap": r["market_cap_str"],
                    "P/E": r["pe_ratio"] or "-",
                    "Fwd P/E": r["forward_pe"] or "-",
                    "Rev Growth": f"{r['revenue_growth']}%" if r["revenue_growth"] else "-",
                    "Analyst Target": f"${r['analyst_target']}" if r["analyst_target"] else "-",
                    "Upside": f"{r['upside_pct']}%" if r["upside_pct"] else "-",
                    "Rating": r["recommendation"] or "-",
                }
                table_data.append(row)

            st.dataframe(table_data, use_container_width=True, hide_index=True)

            st.markdown("---")
            st.markdown("### Run AI Analysis")
            st.markdown("Select stocks from the results above to get full AI analysis with scoring.")

            ticker_options = [r["ticker"] for r in results]
            selected = st.multiselect(
                "Select stocks to analyze (~$0.20 each)",
                ticker_options,
            )

            if selected:
                estimated_cost = len(selected) * 0.20
                st.markdown(f"**Estimated cost:** ~${estimated_cost:.2f}")

                run_analysis = st.button(f"Analyze {len(selected)} stocks", type="primary")

                if run_analysis:
                    progress_bar2 = st.progress(0)
                    status_text2 = st.empty()
                    reports = {}

                    for i, ticker in enumerate(selected):
                        status_text2.markdown(f"**[{i+1}/{len(selected)}]** Analyzing {ticker}...")
                        try:
                            report = analyze_stock(ticker)
                            if report and report.strip():
                                reports[ticker] = report
                                save_report(ticker, report)
                        except Exception as e:
                            reports[ticker] = f"Error: {e}"
                        progress_bar2.progress((i + 1) / len(selected))

                    status_text2.empty()
                    progress_bar2.empty()

                    st.success(f"Done! Analyzed {len(reports)} stocks.")
                    st.markdown("---")

                    if reports:
                        tabs = st.tabs(list(reports.keys()))
                        for tab, (ticker, report) in zip(tabs, reports.items()):
                            with tab:
                                st.markdown(report)
                                st.download_button(
                                    f"Download {ticker}", data=report,
                                    file_name=f"{ticker}_{date.today()}.md",
                                    mime="text/markdown", key=f"screen_dl_{ticker}",
                                )
        else:
            st.warning("No stocks matched your filters. Try loosening the criteria.")


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
                filepath = save_report(ticker, report)
                status_container.empty()
                st.success(f"Analysis complete for {ticker}!")
                st.markdown("---")
                st.markdown(report)
                st.download_button("Download Report (.md)", data=report,
                                   file_name=f"{ticker}_{date.today()}.md", mime="text/markdown")
            else:
                st.error("Empty report. Try again.")
        except Exception as e:
            st.error(f"Error: {e}")

    elif run_button and not ticker:
        st.warning("Enter a ticker symbol.")


elif mode == "Batch Analysis":
    st.title("Batch Analysis")
    st.markdown("Analyze multiple stocks at once.")

    tickers_input = st.text_input("Tickers (comma-separated)", value=", ".join(WATCHLIST))
    run_batch = st.button("Run Batch Analysis", type="primary")

    if run_batch and tickers_input:
        tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
        if not tickers:
            st.warning("Enter at least one ticker.")
        else:
            st.markdown(f"Analyzing **{len(tickers)}** stocks: {', '.join(tickers)}")
            progress_bar = st.progress(0)
            status_text = st.empty()
            reports = {}
            for i, ticker in enumerate(tickers):
                status_text.markdown(f"**[{i+1}/{len(tickers)}]** Analyzing {ticker}...")
                try:
                    report = analyze_stock(ticker)
                    if report and report.strip():
                        reports[ticker] = report
                        save_report(ticker, report)
                except Exception as e:
                    reports[ticker] = f"Error: {e}"
                progress_bar.progress((i + 1) / len(tickers))
            status_text.empty()
            progress_bar.empty()
            st.success(f"Done! Analyzed {len(reports)} stocks.")
            st.markdown("---")
            if reports:
                tabs = st.tabs(list(reports.keys()))
                for tab, (ticker, report) in zip(tabs, reports.items()):
                    with tab:
                        st.markdown(report)
                        st.download_button(f"Download {ticker}", data=report,
                                           file_name=f"{ticker}_{date.today()}.md",
                                           mime="text/markdown", key=f"dl_{ticker}")


elif mode == "Alert Scanner":
    st.title("Alert Scanner")
    st.markdown("Quick scan for actionable signals. **Free — no AI calls.**")

    tickers_input = st.text_input("Tickers to scan", value=", ".join(WATCHLIST))
    run_scan = st.button("Run Alert Scan", type="primary")

    if run_scan and tickers_input:
        tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
        status_text = st.empty()
        progress_bar = st.progress(0)
        all_alerts = []

        for i, ticker in enumerate(tickers):
            status_text.markdown(f"Scanning **{ticker}**...")
            try:
                from tools.market_data import get_stock_data, get_price_history, get_insider_trades
                from tools.alerts import check_alerts
                stock_data = get_stock_data(ticker).model_dump()
                price_data = get_price_history(ticker, "1y")
                insider_data = get_insider_trades(ticker)
                alerts = check_alerts(ticker, stock_data, price_data, insider_data)
                all_alerts.extend(alerts)
            except Exception as e:
                st.warning(f"Error scanning {ticker}: {e}")
            progress_bar.progress((i + 1) / len(tickers))

        status_text.empty()
        progress_bar.empty()

        if all_alerts:
            st.markdown("---")
            high = [a for a in all_alerts if a.severity == "high"]
            med = [a for a in all_alerts if a.severity == "medium"]
            if high:
                st.error(f"**{len(high)} HIGH PRIORITY ALERTS**")
                for a in high:
                    st.markdown(f"**[{a.ticker}] {a.alert_type}**: {a.message}")
            if med:
                st.warning(f"**{len(med)} MEDIUM PRIORITY ALERTS**")
                for a in med:
                    st.markdown(f"**[{a.ticker}] {a.alert_type}**: {a.message}")
            st.markdown("---")
            st.markdown("### Summary")
            st.table([{"Ticker": a.ticker, "Type": a.alert_type,
                       "Severity": a.severity.upper(), "Message": a.message}
                      for a in all_alerts])
        else:
            st.success("All clear! No alerts triggered.")


elif mode == "Past Reports":
    st.title("Past Reports")
    reports_dir = Path("reports")
    report_files = sorted(reports_dir.glob("*.md"), reverse=True)
    if not report_files:
        st.info("No reports yet. Run an analysis first!")
    else:
        for filepath in report_files:
            parts = filepath.stem.split("_", 1)
            ticker = parts[0]
            report_date = parts[1] if len(parts) > 1 else "unknown"
            with st.expander(f"{ticker} - {report_date}"):
                content = filepath.read_text(encoding="utf-8")
                st.markdown(content)
                st.download_button("Download", data=content, file_name=filepath.name,
                                   mime="text/markdown", key=f"past_{filepath.name}")
