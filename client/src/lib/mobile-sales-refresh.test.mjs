import assert from "node:assert/strict";
import test from "node:test";
import { QueryClient, QueryObserver } from "@tanstack/query-core";
import { refreshMobileSalesQueries } from "./mobile-sales-refresh.ts";

const storeKey = (day) => ["/api/sales/summary/stores", "mobile", { end_date: day }];
const monthKey = (level = "stores") => ["mobile-sales-financial-month", `/api/sales/summary/${level}?end_date=2026-09-05`];

function fixture(t) {
  const client = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, retry: false } } });
  const observers = [];
  t.after(() => {
    observers.forEach((observer) => observer.destroy());
    client.clear();
  });
  function watch(key, enabled = true) {
    let calls = 0;
    const options = { queryKey: key, queryFn: async () => ++calls, enabled };
    client.setQueryData(key, 0);
    const observer = new QueryObserver(client, options);
    observer.subscribe(() => {});
    observers.push(observer);
    return { observer, options, calls: () => calls };
  }
  return { client, watch };
}

test("same-date submit refreshes both displayed totals even with infinite/60-second caches", async (t) => {
  const { client, watch } = fixture(t);
  const store = watch(storeKey("2026-09-05"));
  const month = watch(monthKey());
  month.observer.setOptions({ ...month.options, staleTime: 60_000 });
  const desktopKey = ["/api/sales/summary/stores", { end_date: "2026-09-05" }];
  const desktop = watch(desktopKey);
  await refreshMobileSalesQueries(client, { level: "stores", datesChanged: false });
  assert.equal(store.calls(), 1);
  assert.equal(month.calls(), 1);
  assert.equal(desktop.calls(), 0);
  assert.equal(client.getQueryState(desktopKey).isInvalidated, false);
  await refreshMobileSalesQueries(client, { level: "stores", datesChanged: false });
  assert.equal(store.calls(), 2);
  assert.equal(month.calls(), 2);
});

test("changing dates invalidates cached destinations without requesting the old date again", async (t) => {
  const { client, watch } = fixture(t);
  const keyA = storeKey("2026-09-04");
  const keyB = storeKey("2026-09-05");
  const store = watch(keyA);
  const month = watch(monthKey());
  client.setQueryData(keyB, -1);
  await refreshMobileSalesQueries(client, { level: "stores", datesChanged: true });
  assert.equal(store.calls(), 0);
  assert.equal(month.calls(), 1);
  store.observer.setOptions({ ...store.options, queryKey: keyB });
  await new Promise(setImmediate);
  assert.equal(store.calls(), 1);
  assert.equal(client.getQueryData(keyB), 1);
  await refreshMobileSalesQueries(client, { level: "stores", datesChanged: true });
  store.observer.setOptions(store.options);
  await new Promise(setImmediate);
  assert.equal(store.calls(), 2);
  assert.equal(client.getQueryData(keyA), 2);
});

test("submitting from a drilldown refreshes the destination and leaves hidden queries idle", async (t) => {
  const { client, watch } = fixture(t);
  const store = watch(storeKey("2026-09-05"), false);
  const departmentKey = ["/api/sales/summary/departments", "mobile", { end_date: "2026-09-05" }, "1"];
  const department = watch(departmentKey);
  const month = watch(monthKey("departments"));
  client.setQueryData(monthKey(), -1);
  await refreshMobileSalesQueries(client, { level: "departments", datesChanged: false });
  assert.equal(department.calls(), 0);
  assert.equal(month.calls(), 0);
  assert.equal(store.calls(), 0);
  assert.equal(client.getQueryState(departmentKey).isInvalidated, true);
  department.observer.setOptions({ ...department.options, enabled: false });
  store.observer.setOptions({ ...store.options, enabled: true });
  month.observer.setOptions({ ...month.options, queryKey: monthKey() });
  await new Promise(setImmediate);
  assert.equal(store.calls(), 1);
  assert.equal(month.calls(), 1);
  assert.equal(department.calls(), 0);
});
