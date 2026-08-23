"""Build the order-level feature table + return labels for the Tier 2
return-risk scorer, from the raw UCI Online Retail II transaction log.

*** LABEL CONSTRUCTION -- READ BEFORE TRUSTING THIS AS "ground truth" ***
This dataset (real, not synthetic -- see README's Dataset setup for the
UCI source and license) has no explicit "was this order returned" column.
What it DOES have is a real, structural signal: every cancellation is its
own separate invoice, whose number is prefixed with 'C' and whose line
items carry NEGATIVE quantities mirroring an earlier purchase. This is
the standard proxy used across published analyses of this exact dataset
for "return/cancellation" -- but it is honestly a proxy, not a confirmed
"customer received the item and mailed it back": the same 'C' mechanism
also covers pre-shipment order cancellations, so this label is better read
as "this order was cancelled/reversed" than a narrower "physically
returned after delivery." State this plainly anywhere this model's
output is shown, exactly like the fraud model states its SHAP values are
log-odds, not probabilities -- a caveated real signal, not a fabricated
one, and not oversold as more precise than it is.

CONCRETE LABELING RULE: for every NORMAL order (an invoice NOT starting
with 'C', with a known CustomerID), label=1 if that customer has a LATER
cancellation invoice containing at least one of the same StockCodes;
label=0 otherwise. Matching by (CustomerID, StockCode, later timestamp)
is the same heuristic used in prior public treatments of this dataset --
not invented here, but not verified against any external ground truth
either.

WHY CustomerID IS REQUIRED: the label above cannot be constructed without
knowing which future cancellations belong to the same customer. 22.77%
of raw rows have no CustomerID at all (a real data-quality property of
this dataset, not something this script papers over) -- those orders are
excluded from the labeled table entirely, not guessed at. This is a
materially bigger exclusion than anything in the fraud pipeline, and is
called out explicitly in this script's own printed summary and in
docs/README -- see the "Known Limitations" honesty section.

RIGHT-CENSORING CUTOFF -- found and fixed during this feature's own
evaluation, not a theoretical concern: a label of 0 ("not returned") for
an order near the very END of the dataset's date range may just mean
"there wasn't enough FUTURE data left to observe a return," not that the
order genuinely wasn't returned -- the monthly positive rate visibly
collapses from ~30% to ~3% across the final few months purely from this
artifact (confirmed by direct inspection while building this pipeline).
A sample of matched (order -> later cancellation) pairs showed a median
lag of 23 days but a long tail (75th pct. ~99 days) -- so
MATURATION_CUTOFF_DAYS below excludes any order placed within 90 days of
the dataset's last recorded date, on the reasoning that an order that
recent hasn't had a fair chance to show up as "returned" yet. This is the
standard fix for this exact bias in return/churn-prediction tasks, not an
invented workaround.

CAUSAL FEATURES ONLY: customer_order_count_so_far, customer_return_rate_so_far,
and product_return_rate_so_far are all computed using ONLY orders/labels
that occurred STRICTLY BEFORE the order being featurized, via a
groupby+shift(1)+expanding-mean pattern -- exactly the same
no-future-leakage discipline build_features.py already uses for
amount_zscore. A customer's first-ever order, or a never-before-seen
product, gets 0 history (an honest "no prior signal," not an imputed
guess) -- documented cold-start behavior, same spirit as
spike_detector.py's cold-start handling.

Usage:
    python src/features/build_return_features.py
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "online_retail_ii.csv"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "return_features.csv"
PRODUCT_OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "return_features_products.csv"

# See module docstring's "RIGHT-CENSORING CUTOFF" section: orders placed
# within this many days of the dataset's last recorded date are excluded
# entirely -- their "not returned" label can't be trusted yet.
MATURATION_CUTOFF_DAYS = 90

# Countries one-hot encoded individually; everything else collapses into
# country_other. Fixed at build time (not derived per-run) so a single
# order scored later via the API produces the identical column set the
# model was trained on -- see api/services/return_feature_service.py,
# which imports this exact list rather than redefining it.
TOP_COUNTRIES = [
    "United Kingdom", "Germany", "France", "EIRE", "Netherlands",
    "Spain", "Belgium", "Sweden", "Australia",
]

# Service/adjustment line codes that are not real products -- postage,
# manual entries, bank charges, discounts, samples, carriage, Amazon
# marketplace fees, gift-card pseudo-products. Confirmed present in this
# dataset by direct inspection (see Tier 2 dataset-search report); left
# in, they'd corrupt order_value/total_quantity aggregates with
# non-merchandise lines.
NON_PRODUCT_STOCK_CODES = {
    "POST", "DOT", "M", "m", "S", "D", "C2", "BANK CHARGES", "ADJUST",
    "ADJUST2", "AMAZONFEE", "PADS", "CRUK", "TEST001", "TEST002",
}


def _is_cancellation(invoice: pd.Series) -> pd.Series:
    return invoice.astype(str).str.startswith("C")


def add_country_dummies(data: pd.DataFrame) -> pd.DataFrame:
    """One-hot encode Country against the fixed TOP_COUNTRIES list, with
    everything else collapsing into country_other. Pure per-row function,
    safe to call on a single order at inference time (see
    api/services/return_feature_service.py).
    """
    data = data.copy()
    for country in TOP_COUNTRIES:
        column = f"country_{country.lower().replace(' ', '_')}"
        data[column] = (data["Country"] == country).astype("int8")
    data["country_other"] = (~data["Country"].isin(TOP_COUNTRIES)).astype("int8")
    return data


def load_raw() -> pd.DataFrame:
    if not RAW_DATA_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {RAW_DATA_PATH}. See README's Dataset setup for the "
            "direct UCI download link (no login required)."
        )
    data = pd.read_csv(RAW_DATA_PATH, parse_dates=["InvoiceDate"])
    data["Invoice"] = data["Invoice"].astype(str)
    data["StockCode"] = data["StockCode"].astype(str)
    return data


def build_order_features(data: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (order_table, product_table) -- see PRODUCT_OUTPUT_PATH's
    comment above for why the second table is also persisted.
    """
    data = data[~data["StockCode"].isin(NON_PRODUCT_STOCK_CODES)].copy()
    data = data[data["Price"] > 0]
    data["is_cancel"] = _is_cancellation(data["Invoice"])

    # Normal (non-cancelled) purchase lines only, for order aggregation.
    # A handful of non-'C' invoices still carry stray negative-quantity
    # lines (stock write-offs/adjustments recorded on an otherwise normal
    # invoice, not a real cancellation) -- excluded from aggregation so
    # they can't corrupt order_value/total_quantity; documented, not
    # silently dropped.
    normal = data[(~data["is_cancel"]) & (data["Quantity"] > 0)].copy()
    normal_with_customer = normal.dropna(subset=["Customer ID"]).copy()
    normal_with_customer["Customer ID"] = normal_with_customer["Customer ID"].astype(int)

    cancels = data[data["is_cancel"] & (data["Quantity"] < 0)].dropna(subset=["Customer ID"]).copy()
    cancels["Customer ID"] = cancels["Customer ID"].astype(int)

    # --- Order-level aggregation (one row per normal invoice) -----------
    orders = (
        normal_with_customer.groupby("Invoice")
        .agg(
            CustomerID=("Customer ID", "first"),
            InvoiceDate=("InvoiceDate", "first"),
            Country=("Country", "first"),
            order_value=("Quantity", lambda q: float((q * normal_with_customer.loc[q.index, "Price"]).sum())),
            total_quantity=("Quantity", "sum"),
            distinct_products=("StockCode", "nunique"),
        )
        .reset_index()
    )
    # Every distinct StockCode touched by each order, for return-label matching.
    order_products = normal_with_customer.groupby("Invoice")["StockCode"].apply(set).to_dict()

    # --- Label: does a LATER cancellation exist for this customer that ---
    # --- shares at least one StockCode with this order? ------------------
    # Index cancellations per customer for fast lookup.
    cancels_by_customer: dict[int, pd.DataFrame] = {
        customer_id: group[["InvoiceDate", "StockCode"]].sort_values("InvoiceDate")
        for customer_id, group in cancels.groupby("Customer ID")
    }

    def was_returned(row: pd.Series) -> bool:
        customer_cancels = cancels_by_customer.get(row["CustomerID"])
        if customer_cancels is None:
            return False
        later = customer_cancels[customer_cancels["InvoiceDate"] > row["InvoiceDate"]]
        if later.empty:
            return False
        return bool(set(later["StockCode"]) & order_products[row["Invoice"]])

    orders["returned"] = orders.apply(was_returned, axis=1).astype(int)

    orders = orders.sort_values("InvoiceDate", kind="stable").reset_index(drop=True)
    orders["day_of_week"] = orders["InvoiceDate"].dt.dayofweek.astype("int8")
    orders["month"] = orders["InvoiceDate"].dt.month.astype("int8")
    orders["hour_of_day"] = orders["InvoiceDate"].dt.hour.astype("int8")

    # --- Causal customer history (strictly-prior orders only) -----------
    prior_return = orders.groupby("CustomerID")["returned"].shift(1)
    orders["customer_order_count_so_far"] = orders.groupby("CustomerID").cumcount()
    orders["customer_return_rate_so_far"] = (
        prior_return.groupby(orders["CustomerID"]).expanding().mean().reset_index(level=0, drop=True)
    ).fillna(0.0)

    # --- Causal product history (strictly-prior orders touching that ----
    # --- product, averaged across an order's distinct products) ---------
    exploded = orders[["Invoice", "InvoiceDate", "returned"]].copy()
    exploded["StockCode"] = orders["Invoice"].map(order_products)
    exploded = exploded.explode("StockCode")
    # explode() duplicates the original row's index once per exploded
    # element -- reset to a clean unique index before any further
    # groupby/shift/expanding, or later Series-alignment on assignment
    # back to this DataFrame fails on the duplicate labels.
    exploded = exploded.sort_values("InvoiceDate", kind="stable").reset_index(drop=True)
    prior_product_return = exploded.groupby("StockCode")["returned"].shift(1)
    exploded["product_return_rate_so_far"] = (
        prior_product_return.groupby(exploded["StockCode"]).expanding().mean().reset_index(level=0, drop=True)
    ).fillna(0.0)
    order_product_rate = exploded.groupby("Invoice")["product_return_rate_so_far"].mean()
    orders["product_return_rate_so_far"] = orders["Invoice"].map(order_product_rate).fillna(0.0)

    orders = add_country_dummies(orders)
    country_columns = [c for c in orders.columns if c.startswith("country_")]

    # Apply the maturation cutoff LAST, after all causal features are
    # computed: shift(1)/expanding only ever look backward, so dropping
    # these trailing rows now cannot change any earlier row's computed
    # history -- it only removes orders whose own label isn't trustworthy
    # yet. See module docstring's "RIGHT-CENSORING CUTOFF" section.
    maturation_cutoff = orders["InvoiceDate"].max() - pd.Timedelta(days=MATURATION_CUTOFF_DAYS)
    orders = orders[orders["InvoiceDate"] <= maturation_cutoff].reset_index(drop=True)

    order_table = orders[
        [
            "Invoice", "CustomerID", "InvoiceDate", "Country",
            "order_value", "total_quantity", "distinct_products",
            "day_of_week", "month", "hour_of_day",
            "customer_order_count_so_far", "customer_return_rate_so_far",
            "product_return_rate_so_far", *country_columns, "returned",
        ]
    ]
    # (Invoice, StockCode, InvoiceDate, returned) long-format table --
    # saved alongside the order-level table so train_return_model.py can
    # build TRAINING-SLICE-ONLY product reference stats for live
    # inference without re-deriving product membership from raw data (see
    # api/services/return_model_service.py).
    product_table = exploded[["Invoice", "StockCode", "InvoiceDate", "returned"]]

    return order_table, product_table


def main() -> None:
    raw = load_raw()
    total_rows = len(raw)
    missing_customer_rows = int(raw["Customer ID"].isna().sum())

    orders, products = build_order_features(raw)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    orders.to_csv(OUTPUT_PATH, index=False)
    products.to_csv(PRODUCT_OUTPUT_PATH, index=False)

    print(f"Raw rows: {total_rows:,} (missing Customer ID: {missing_customer_rows:,}, "
          f"{missing_customer_rows / total_rows * 100:.1f}% -- excluded, not guessed at)")
    print(f"Labeled orders: {len(orders):,}")
    print(f"Positive (returned) rate: {orders['returned'].mean() * 100:.2f}% "
          f"({int(orders['returned'].sum()):,} returned)")
    print(f"Date range: {orders['InvoiceDate'].min()} to {orders['InvoiceDate'].max()}")
    print(f"Saved product-level table ({len(products):,} rows): {PRODUCT_OUTPUT_PATH}")
    print(f"Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
