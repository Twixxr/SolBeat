"""Patch the static dashboard so the generated outlook appears on the Overview tab."""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
HTML = ROOT / "dashboard" / "index.html"

source = HTML.read_text(encoding="utf-8")
pattern = re.compile(r"function overviewInsightSentence\(market, tvl, val\)\{.*?\n\}\n\nfunction renderNetwork\(\)", re.S)
replacement = r'''function overviewInsightSentence(market, tvl, val){
  const outlook = REPORT.outlook || {};
  if(outlook.summary){
    const rating = outlook.rating || "Current Outlook";
    const positives = (outlook.positive_signals || []).slice(0, 2).join("; ");
    const risks = (outlook.risks_to_watch || []).slice(0, 2).join("; ");
    return "<strong>Solana outlook: " + rating + "</strong> — " + outlook.summary +
      (positives ? " <span style=\"color:var(--green)\">Positive: " + positives + ".</span>" : "") +
      (risks ? " <span style=\"color:var(--warn)\">Watch: " + risks + ".</span>" : "");
  }

  if(market.price_usd === null || market.price_usd === undefined) return null;
  const priceDir = market.price_change_pct_24h > 0 ? "up" : (market.price_change_pct_24h < 0 ? "down" : "flat");
  const tvlDir = tvl.tvl_change_pct_24h > 0 ? "up" : (tvl.tvl_change_pct_24h < 0 ? "down" : "flat");
  return "SOL is trading at <strong>" + fmtUsd(market.price_usd) + "</strong>, " + priceDir +
    " " + Math.abs(market.price_change_pct_24h || 0).toFixed(1) + "% over 24 hours, while DeFi TVL is " +
    tvlDir + " " + Math.abs(tvl.tvl_change_pct_24h || 0).toFixed(1) + "% and <strong>" +
    fmtNum(val.active_count,0) + " validators</strong> are active.";
}

function renderNetwork()'''

updated, count = pattern.subn(replacement, source, count=1)
if count != 1:
    raise SystemExit("Could not find overviewInsightSentence in dashboard/index.html; refusing to modify the file.")

HTML.write_text(updated, encoding="utf-8")
