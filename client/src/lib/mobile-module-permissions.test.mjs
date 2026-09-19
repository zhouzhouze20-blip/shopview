import assert from "node:assert/strict";
import test from "node:test";
import {
  MODULE_PERMISSION_DEPENDENCIES,
  MODULE_PERMISSION_REQUIREMENTS,
  canAccessModule,
  getDefaultMobileRolePermissionIds,
} from "./module-permissions.ts";

const businessUser = (permissionCodes) => ({
  role_codes: ["viewer"],
  permission_codes: permissionCodes,
});

test("mobile modules have independent permission codes and matching business dependencies", () => {
  assert.deepEqual(MODULE_PERMISSION_REQUIREMENTS["mobile-sales-dashboard"], ["mobile.sales.view"]);
  assert.deepEqual(MODULE_PERMISSION_REQUIREMENTS["mobile-contracts"], ["mobile.contracts.view"]);
  assert.deepEqual(MODULE_PERMISSION_REQUIREMENTS["mobile-inventory"], ["mobile.inventory.view"]);
  assert.deepEqual(MODULE_PERMISSION_REQUIREMENTS["mobile-revenue-dashboard"], ["mobile.revenue_dashboard.view"]);
  assert.deepEqual(MODULE_PERMISSION_REQUIREMENTS["mobile-rental-receivables"], ["mobile.rental_receivables.view"]);
  assert.deepEqual(MODULE_PERMISSION_REQUIREMENTS["mobile-coupon-followups"], ["mobile.coupon_followup.view"]);
  assert.deepEqual(MODULE_PERMISSION_REQUIREMENTS["mobile-supplier-payments"], ["mobile.supplier_payments.view"]);

  assert.deepEqual(MODULE_PERMISSION_DEPENDENCIES["mobile-sales-dashboard"], ["sales.view"]);
  assert.deepEqual(MODULE_PERMISSION_DEPENDENCIES["mobile-contracts"], ["contract.view"]);
  assert.deepEqual(MODULE_PERMISSION_DEPENDENCIES["mobile-inventory"], ["sales.inventory.view"]);
  assert.deepEqual(MODULE_PERMISSION_DEPENDENCIES["mobile-revenue-dashboard"], ["revenue.dashboard.view"]);
  assert.deepEqual(MODULE_PERMISSION_DEPENDENCIES["mobile-rental-receivables"], ["settlement.view"]);
  assert.deepEqual(MODULE_PERMISSION_DEPENDENCIES["mobile-coupon-followups"], undefined);
  assert.deepEqual(MODULE_PERMISSION_DEPENDENCIES["mobile-supplier-payments"], undefined);
});

test("mobile access requires both the mobile module permission and its business permission", () => {
  assert.equal(
    canAccessModule(businessUser(["mobile.sales.view", "sales.view"]), "mobile-sales-dashboard"),
    true,
  );
  assert.equal(canAccessModule(businessUser(["sales.view"]), "mobile-sales-dashboard"), false);
  assert.equal(canAccessModule(businessUser(["mobile.sales.view"]), "mobile-sales-dashboard"), false);
});

test("administrators retain access to every mobile module", () => {
  const admin = { role_codes: ["system_admin"], permission_codes: [] };
  assert.equal(canAccessModule(admin, "mobile-sales-dashboard"), true);
  assert.equal(canAccessModule(admin, "mobile-contracts"), true);
  assert.equal(canAccessModule(admin, "mobile-inventory"), true);
  assert.equal(canAccessModule(admin, "mobile-revenue-dashboard"), true);
  assert.equal(canAccessModule(admin, "mobile-rental-receivables"), true);
  assert.equal(canAccessModule(admin, "mobile-coupon-followups"), true);
  assert.equal(canAccessModule(admin, "mobile-supplier-payments"), true);
});

test("new roles default to the three baseline mobile permissions only", () => {
  const permissions = [
    { id: 9, permission_code: "mobile.inventory.view" },
    { id: 7, permission_code: "mobile.sales.view" },
    { id: 8, permission_code: "mobile.contracts.view" },
    { id: 10, permission_code: "mobile.revenue_dashboard.view" },
  ];
  assert.deepEqual(getDefaultMobileRolePermissionIds(permissions), [7, 8, 9]);
});
