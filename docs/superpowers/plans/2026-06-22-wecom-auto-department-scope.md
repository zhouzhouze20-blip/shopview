# WeCom Auto Department Scope Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically create one department-level `business_scope/view` policy from a user's Enterprise WeChat department while preserving manually added extra ranges.

**Architecture:** Add a focused service under `python_app/services` that maps Enterprise WeChat department names to business department codes and upserts only the auto policy identified by `wecom-auto-department:<user_id>`. Reuse it from Enterprise WeChat contact sync and call it as a non-blocking login fallback after a successful Enterprise WeChat login.

**Tech Stack:** Python 3, SQLAlchemy ORM, existing `data_policies` / `data_policy_items` models, existing Enterprise WeChat sync and auth routers, `unittest`.

---

### Task 1: Add Department Scope Service

**Files:**
- Create: `python_app/services/wecom_department_scope.py`
- Test: `tests/test_wecom_department_scope.py`

- [ ] **Step 1: Write failing service tests**

Create `tests/test_wecom_department_scope.py` with tests for alias resolution, exact normalized name matching, auto policy replacement, and preserving non-auto manual policies.

- [ ] **Step 2: Run the new tests and verify they fail**

Run: `PYTHONPATH=python_app python3 -m unittest tests.test_wecom_department_scope -v`

Expected: import failure because `services.wecom_department_scope` does not exist.

- [ ] **Step 3: Implement `python_app/services/wecom_department_scope.py`**

Implement:

- `AUTO_SCOPE_EXTERNAL_PREFIX = "wecom-auto-department"`
- `normalize_department_name(value)`
- `department_leaf_names(department_path)`
- `resolve_business_department(db, department_path)`
- `refresh_auto_department_scope(db, user, wecom_user_id, department_path)`

The refresh function deletes and recreates only policies whose `external_scope_id` equals `wecom-auto-department:<user_id>`, writes `department:<business dept_code>`, and returns a small result object with `updated`, `department_code`, `department_name`, and `reason`.

- [ ] **Step 4: Run service tests and verify they pass**

Run: `PYTHONPATH=python_app python3 -m unittest tests.test_wecom_department_scope -v`

Expected: all tests pass.

### Task 2: Wire Contact Sync

**Files:**
- Modify: `python_app/sync_wecom_contacts.py`
- Test: `tests/test_wecom_department_scope.py`

- [ ] **Step 1: Add sync tests for the existing refresh behavior**

Extend the service tests to cover that automatic department refresh can be called independent of role-scope rules and does not delete legacy/manual policies.

- [ ] **Step 2: Update sync to use the service**

Import `refresh_auto_department_scope` and call it for every applied member with a department. Increment stats:

- `wecom_auto_department_scopes_refreshed`
- `wecom_auto_department_scope_failures`

Leave existing role assignment intact. Stop using `_department_scope_values(...)` as the source of default business data scope for the user.

- [ ] **Step 3: Run sync-related tests**

Run: `PYTHONPATH=python_app python3 -m unittest tests.test_wecom_department_scope -v`

Expected: all tests pass.

### Task 3: Wire Enterprise WeChat Login Fallback

**Files:**
- Modify: `python_app/services/wecom_client.py`
- Modify: `python_app/routers/auth.py`

- [ ] **Step 1: Add member profile fetch helper**

Add `get_user_detail(config, userid)` to `python_app/services/wecom_client.py`, using the existing app access token and `/user/get` endpoint.

- [ ] **Step 2: Refresh scope after successful Enterprise WeChat login**

In `wecom_callback`, after a bound and active user is found, fetch the user detail. If a department list is returned, resolve the department name if possible and call `refresh_auto_department_scope(...)`. Log failures but do not block login.

- [ ] **Step 3: Compile changed Python files**

Run: `python3 -m py_compile python_app/services/wecom_department_scope.py python_app/sync_wecom_contacts.py python_app/services/wecom_client.py python_app/routers/auth.py`

Expected: command exits 0.

### Task 4: Production Dry Run Diagnostic

**Files:**
- Create: `python_app/diagnose_wecom_department_scopes.py`

- [ ] **Step 1: Add a read-only diagnostic script**

Create a script that reads current users with WeCom identities, their primary user department post or synced department where available, runs department mapping, and prints counts for mapped, missing department, and missing business mapping. It must not write unless a future explicit `--apply` is added.

- [ ] **Step 2: Run compile and focused tests**

Run:

```bash
PYTHONPATH=python_app python3 -m unittest tests.test_wecom_department_scope -v
python3 -m py_compile python_app/diagnose_wecom_department_scopes.py
```

Expected: tests pass and compile exits 0.
