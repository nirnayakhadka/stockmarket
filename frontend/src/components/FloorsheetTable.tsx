import { useState, useEffect } from "react";
import { fetchFloorsheet } from "../api/mappers";
import type { ApiFloorsheetTransaction } from "../api/mappers";

interface BrokerNet {
  broker: string;
  buyQty: number;
  sellQty: number;
  netQty: number;
}

function aggregateByBroker(
  transactions: ApiFloorsheetTransaction[],
): BrokerNet[] {
  const map = new Map<string, BrokerNet>();

  for (const t of transactions) {
    const buyer = map.get(t.buyer_broker) ?? {
      broker: t.buyer_broker,
      buyQty: 0,
      sellQty: 0,
      netQty: 0,
    };
    buyer.buyQty += t.quantity;
    buyer.netQty += t.quantity;
    map.set(t.buyer_broker, buyer);

    const seller = map.get(t.seller_broker) ?? {
      broker: t.seller_broker,
      buyQty: 0,
      sellQty: 0,
      netQty: 0,
    };
    seller.sellQty += t.quantity;
    seller.netQty -= t.quantity;
    map.set(t.seller_broker, seller);
  }

  return Array.from(map.values()).sort(
    (a, b) => b.buyQty + b.sellQty - (a.buyQty + a.sellQty),
  );
}

export default function FloorsheetTable({ companyId }: { companyId: number }) {
  const [date, setDate] = useState<string>(() =>
    new Date().toISOString().slice(0, 10),
  );
  const [transactions, setTransactions] = useState<ApiFloorsheetTransaction[]>(
    [],
  );
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    fetchFloorsheet(companyId, date)
      .then((res) => {
        if (!cancelled) setTransactions(res.transactions);
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || "Failed to load floorsheet");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [companyId, date]);

  const brokerRows = aggregateByBroker(transactions);
  const mostActiveBuyer = [...brokerRows].sort(
    (a, b) => b.buyQty - a.buyQty,
  )[0];
  const mostActiveSeller = [...brokerRows].sort(
    (a, b) => b.sellQty - a.sellQty,
  )[0];

  return (
    <section className="bg-panel border border-panel-border rounded-xl px-5 py-4.5 mb-5">
      <div className="flex items-center justify-between mb-3.5">
        <h2 className="text-[15px] font-semibold">
          Floorsheet — broker activity
        </h2>
        <input
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          className="bg-[#1e2430] border border-panel-border rounded-lg px-2.5 py-1 text-xs text-white"
        />
      </div>

      {loading && <p className="text-muted text-sm">Loading floorsheet…</p>}
      {error && <p className="text-negative text-sm">{error}</p>}

      {!loading && !error && transactions.length === 0 && (
        <p className="text-muted text-sm">
          No floorsheet transactions for this date. The official NEPSE
          floorsheet only exposes the current trading day — this endpoint only
          has data for days collected while they were live.
        </p>
      )}

      {!loading && transactions.length > 0 && (
        <>
          <div className="grid grid-cols-2 gap-3.5 mb-4">
            <div className="text-sm">
              <span className="text-muted text-xs block">
                Most active buyer
              </span>
              <span className="font-semibold text-positive">
                {mostActiveBuyer?.broker} (
                {mostActiveBuyer?.buyQty.toLocaleString()})
              </span>
            </div>
            <div className="text-sm">
              <span className="text-muted text-xs block">
                Most active seller
              </span>
              <span className="font-semibold text-negative">
                {mostActiveSeller?.broker} (
                {mostActiveSeller?.sellQty.toLocaleString()})
              </span>
            </div>
          </div>

          <table className="w-full border-collapse">
            <thead>
              <tr>
                {["Broker", "Buy Qty", "Sell Qty", "Net Qty"].map((h) => (
                  <th
                    key={h}
                    className="text-left text-[11px] uppercase tracking-wide text-muted px-2.5 py-2 border-b border-panel-border"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {brokerRows.map((b) => (
                <tr key={b.broker}>
                  <td className="px-2.5 py-2 border-b border-[#1e222c] text-sm font-medium">
                    {b.broker}
                  </td>
                  <td className="px-2.5 py-2 border-b border-[#1e222c] text-sm text-positive">
                    {b.buyQty.toLocaleString()}
                  </td>
                  <td className="px-2.5 py-2 border-b border-[#1e222c] text-sm text-negative">
                    {b.sellQty.toLocaleString()}
                  </td>
                  <td
                    className={`px-2.5 py-2 border-b border-[#1e222c] text-sm ${b.netQty >= 0 ? "text-positive" : "text-negative"}`}
                  >
                    {b.netQty >= 0 ? "+" : ""}
                    {b.netQty.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </section>
  );
}
