import assert from "node:assert/strict";
import test from "node:test";
import { getSystemConfigQueryScope } from "./system-config-query-scope.ts";

test("role management loads only role and permission data", () => {
  assert.deepEqual(getSystemConfigQueryScope("roles"), {
    stores: false,
    permissions: true,
    posts: false,
    roles: true,
    departments: false,
    users: false,
    policies: false,
    wecomRules: false,
    meta: false,
    contractPermissionOptions: false,
    contractPermissions: false,
  });
});

test("each configuration tab enables the data required by its forms", () => {
  const users = getSystemConfigQueryScope("users");
  assert.equal(users.stores, true);
  assert.equal(users.posts, true);
  assert.equal(users.roles, true);
  assert.equal(users.departments, true);
  assert.equal(users.users, true);

  const departments = getSystemConfigQueryScope("departments");
  assert.equal(departments.stores, true);
  assert.equal(departments.departments, true);
  assert.equal(departments.users, true);

  const policies = getSystemConfigQueryScope("policies");
  assert.equal(policies.policies, true);
  assert.equal(policies.meta, true);

  const contractPermissions = getSystemConfigQueryScope("contract-permissions");
  assert.equal(contractPermissions.contractPermissionOptions, true);
  assert.equal(contractPermissions.contractPermissions, true);
});
