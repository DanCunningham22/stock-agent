import streamlit as st
from pathlib import Path
from datetime import date

from orchestrator import analyze_stock
from tools.cache import init_cache
from tools.research_engine import run_daily_model, backtest_portfolio
from config import WATCHLIST

st.set_page_config(page_title="Stock Research Agent", page_icon="📈", layout="wide")
init_cache()
Path("reports").mkdir(exist_ok=True)

# ============================================================
# Sidebar
# ============================================================

st.sidebar.title("Stock Research Agent")
st.sidebar.markdown("AI research + Quant Screener + Alerts")
st.sidebar.markdown("---")

mode = st.sidebar.radio(
    "Mode",
    ["Quant Screener", "Single Stock", "Batch Analysis", "Alert Scanner", "Past Reports"]
)

st.sidebar.markdown("---")
st.sidebar.markdown(
    "**Quant Model:** Free\n\n"
    "**AI Deep Dive:** ~$0.15-0.20/stock\n\n"
    "**Backtest:** Free\n\n"
    "*Not financial advice.*"
)

# ============================================================
# Helper
# ============================================================

def save_report(ticker, report):
    output_dir = Path("reports")
    output_dir.mkdir(exist_ok=True)
    filepath = output_dir / f"{ticker}_{date.today()}.md"
    filepath.write_text(report, encoding="utf-8")
    return filepath


# ============================================================
# QUANT SCREENER
# ============================================================

if mode == "Quant Screener":

    st.title("📊 Quant Multi-Factor Research Model")

    st.markdown("""
    This model ranks **all liquid US stocks** using:
    - Value
    - Growth
    - Quality
    - Momentum
    - Bounce
    - Analyst Upside
    - Liquidity
    
    Returns **Top 20 Equal-Weight Long Portfolio**
    """)

    run_model = st.button("Run Daily Quant Model", type="primary")

    if run_model:
        with st.spinner("Running full factor model... (First run may take several minutes)"):
            results = run_daily_model()

        st.success("Model complete!")

        st.markdown("## 🏆 Top 20 Portfolio (Equal Weight)")

        display_df = results.copy()

        columns_to_show = [
            "ticker",
            "total_score",
            "rank",
            "rank_change",
            "value_score",
            "growth_score",
            "quality_score",
            "momentum_score",
            "bounce_score",
            "analyst_score",
            "liquidity_score",
            "volatility_score"
        ]

        existing_cols = [c for c in columns_to_show if c in display_df.columns]

        display_df = display_df[existing_cols]

        st.dataframe(display_df, use_container_width=True)

        # ========================================================
        # AI Deep Dive
        # ========================================================

        st.markdown("---")
        st.markdown("## 🤖 AI Deep Dive")

        ticker_options = display_df["ticker"].tolist()
        selected = st.multiselect(
            "Select stocks for AI analysis (~$0.20 each)",
            ticker_options
        )

        if selected:
            cost = len(selected) * 0.20
            st.markdown(f"**Estimated cost:** ~${cost:.2f}")

            if st.button(f"Analyze {len(selected)} Stocks", type="primary"):
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

                if reports:
                    tabs = st.tabs(list(reports.keys()))
                    for tab, (t, report) in zip(tabs, reports.items()):
                        with tab:
                            st.markdown(report)
                            st.download_button(
                                f"Download {t}",
                                data=report,
                                file_name=f"{t}_{date.today()}.md",
                                mime="text/markdown",
                                key=f"quant_dl_{t}"
                            )

    # ========================================================
    # Backtesting
    # ========================================================

    st.markdown("---")
    st.markdown("## 📈 Optional Backtest")

    col1, col2 = st.columns(2)

    with col1:
        bt_30 = st.button("Backtest 30 Days")
    with col2:
        bt_60 = st.button("Backtest 60 Days")

    if bt_30:
        with st.spinner("Running 30-day backtest..."):
            result = backtest_portfolio(30)

        if result:
            st.write("Model Return:", round(result["total_return"] * 100, 2), "%")
            st.write("SPY Return:", round(result["spy_return"] * 100, 2), "%")
            st.write("Alpha:", round(result["alpha"] * 100, 2), "%")
            st.write("Sharpe:", round(result["sharpe"], 2))
            st.write("Max Drawdown:", round(result["max_drawdown"] * 100, 2), "%")

    if bt_60:
        with st.spinner("Running 60-day backtest..."):
            result = backtest_portfolio(60)

        if result:
            st.write("Model Return:", round(result["total_return"] * 100, 2), "%")
            st.write("SPY Return:", round(result["spy_return"] * 100, 2), "%")
            st.write("Alpha:", round(result["alpha"] * 100, 2), "%")
            st.write("Sharpe:", round(result["sharpe"], 2))
            st.write("Max Drawdown:", round(result["max_drawdown"] * 100, 2), "%")

# ============================================================
# SINGLE STOCK
# ============================================================

elif mode == "Single Stock":

    st.title("Analyze a Stock")

    col1, col2 = st.columns([3, 1])

    with col1:
        ticker = st.text_input("Ticker Symbol", placeholder="e.g. AAPL").strip().upper()

    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        run_button = st.button("Analyze", type="primary", use_container_width=True)

    if run_button and ticker:
        with st.spinner(f"Analyzing {ticker}..."):
            try:
                report = analyze_stock(ticker)
                if report and report.strip():
                    save_report(ticker, report)
                    st.success("Analysis complete!")
                    st.markdown(report)
                    st.download_button(
                        "Download Report",
                        data=report,
                        file_name=f"{ticker}_{date.today()}.md",
                        mime="text/markdown"
                    )
                else:
                    st.error("Empty report.")
            except Exception as e:
                st.error(f"Error: {e}")

    elif run_button:
        st.warning("Enter a ticker symbol.")


# ============================================================
# BATCH ANALYSIS
# ============================================================

elif mode == "Batch Analysis":

    st.title("Batch Analysis")

    tickers_input = st.text_input("Tickers (comma-separated)", value=", ".join(WATCHLIST))

    if st.button("Run Batch Analysis", type="primary") and tickers_input:
        tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
        bar = st.progress(0)
        reports = {}

        for i, t in enumerate(tickers):
            try:
                report = analyze_stock(t)
                if report and report.strip():
                    reports[t] = report
                    save_report(t, report)
            except Exception as e:
                reports[t] = f"Error: {e}"

            bar.progress((i+1) / len(tickers))

        bar.empty()

        if reports:
            tabs = st.tabs(list(reports.keys()))
            for tab, (t, rp) in zip(tabs, reports.items()):
                with tab:
                    st.markdown(rp)
                    st.download_button(
                        f"Download {t}",
                        data=rp,
                        file_name=f"{t}_{date.today()}.md",
                        mime="text/markdown",
                        key=f"batch_dl_{t}"
                    )


# ============================================================
# ALERT SCANNER
# ============================================================

elif mode == "Alert Scanner":

    st.title("Alert Scanner")

    tickers_input = st.text_input("Tickers to scan", value=", ".join(WATCHLIST))

    if st.button("Run Alert Scan", type="primary") and tickers_input:
        tickers = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]
        st.info("Scanning...")

        from tools.market_data import get_stock_data, get_price_history, get_insider_trades
        from tools.alerts import check_alerts

        all_alerts = []

        for t in tickers:
            try:
                sd = get_stock_data(t).model_dump()
                pd = get_price_history(t, "1y")
                id = get_insider_trades(t)
                alerts = check_alerts(t, sd, pd, id)
                all_alerts.extend(alerts)
            except Exception as e:
                st.warning(f"Error scanning {t}: {e}")

        if all_alerts:
            for a in all_alerts:
                st.markdown(f"**[{a.ticker}] {a.alert_type}**: {a.message}")
        else:
            st.success("All clear!")


# ============================================================
# PAST REPORTS
# ============================================================

elif mode == "Past Reports":

    st.title("Past Reports")

    reports_dir = Path("reports")
    files = sorted(reports_dir.glob("*.md"), reverse=True)

    if not files:
        st.info("No reports yet.")
    else:
        for f in files:
            with st.expander(f.name):
                content = f.read_text(encoding="utf-8")
                st.markdown(content)
                st.download_button(
                    "Download",
                    data=content,
                    file_name=f.name,
                    mime="text/markdown",
                    key=f"past_{f.name}"
                )