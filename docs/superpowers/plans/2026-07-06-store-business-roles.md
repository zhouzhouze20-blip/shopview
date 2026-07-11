# Store Business Roles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Assign meeting/training users to functional store roles for operations, planning, and customer service while constraining their data scope to their actual store or stores.

**Architecture:** Extend the existing `work/adjust_operations_store_scopes.py` maintenance script rather than adding a second one. The script derives target users from `meeting-permission-check.csv`, maps department names to one functional role, aggregates store scopes by user, removes broad legacy roles from those targets, and replaces active user `business_scope/view` policies with an explicit store policy.

**Tech Stack:** Python 3, SQLAlchemy models in `python_app`, unittest tests in `work/test_adjust_operations_store_scopes.py`.

---

### Task 1: Target Selection And Role Mapping

**Files:**
- Modify: `work/test_adjust_operations_store_scopes.py`
- Modify: `work/adjust_operations_store_scopes.py`

- [ ] **Step 1: Write failing tests**

Add tests that assert `training_specs()` returns 程益 as `store_operations` with store `1`, 陆雅虹 as `store_operations` with store `3`, 陈婷 as `store_planning` with store `3`, and 白海燕 as `store_customer_service` with stores `1` and `3`.

- [ ] **Step 2: Run tests and verify failure**

Run: `python3 -m unittest work.test_adjust_operations_store_scopes -v`

- [ ] **Step 3: Implement target selection**

Update `UserSpec` to carry `store_ids` and a functional `role_code`, add role mapping helpers, aggregate CSV rows by `user_id`, and retain manual target users as store-scope records.

- [ ] **Step 4: Run tests and verify pass**

Run: `python3 -m unittest work.test_adjust_operations_store_scopes -v`

### Task 2: Database Role And Scope Application

**Files:**
- Modify: `work/adjust_operations_store_scopes.py`

- [ ] **Step 1: Ensure functional roles**

Add role upsert helpers for `store_operations / 门店营运`, `store_planning / 门店企划`, and `store_customer_service / 门店客服`. Existing roles with those codes or names are reused.

- [ ] **Step 2: Replace broad user roles for targets**

Remove broad roles such as `super_admin`, `system_admin`, `store_admin`, `store_director`, `dept_manager`, `group_manager`, `contract_viewer`, and legacy `xsj_qh` from managed target users before adding their functional role.

- [ ] **Step 3: Replace user business scope**

Deactivate active target-user `business_scope/view` policies other than the managed policy, then write one managed policy with the target stores.

- [ ] **Step 4: Verify dry-run and tests**

Run:
`python3 -m unittest work.test_adjust_operations_store_scopes -v`
`python3 work/adjust_operations_store_scopes.py`
