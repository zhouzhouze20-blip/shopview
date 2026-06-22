# Enterprise WeChat Auto Department Scope Design

## Background

ShopView business pages such as sales, contracts, settlements, and revenue use `business_scope/view` data policies to filter records. A user can have the correct module permissions and still see no data when no user-level business scope exists.

The current issue was reproduced with Jiang Jiawei. The user has the department manager role and view permissions, but no active `business_scope/view` policy. The expected department exists in business data as `6010102 / 中心四部(男装)`, so the failure is caused by missing user data scope, not missing business data.

## Goal

When a user signs in through Enterprise WeChat, ShopView should automatically create or refresh that user's default data scope from the user's Enterprise WeChat department.

The automatic scope covers exactly one department because each person belongs to one Enterprise WeChat department. If one person manages additional departments, an administrator adds those extra ranges manually.

## Non-Goals

- Do not infer multi-department management from job title, department name, or role.
- Do not grant broad store-level access when department mapping is missing.
- Do not overwrite manually added data ranges.
- Do not change business module filtering logic in sales, contracts, settlements, revenue, or dashboard APIs unless a bug is found during implementation.

## Data Model

Automatic department scopes use the existing `data_policies` and `data_policy_items` tables.

Automatic policy:

- `subject_type = USER`
- `subject_id = users.user_id`
- `resource_code = business_scope`
- `action_code = view`
- `scope_mode = CUSTOM`
- `effect = ALLOW`
- `source_type = WECOM`
- `source_system = wecom`
- `external_scope_id = wecom-auto-department:<user_id>`
- `external_scope_name = <real_name> 企业微信自动部门范围`

Automatic policy item:

- `dimension_type = department`
- `dimension_value = <business department code>`
- `include_children = false`

Manual extra ranges must use a distinct source marker, such as `source_type = MANUAL` and `source_system = shopview`, or another non-auto `external_scope_id`. The auto-refresh job only replaces the matching `wecom-auto-department:<user_id>` policy.

## Department Mapping

Enterprise WeChat department names are not always identical to business department names in `counter_groups` or `departments`. The auto scope must map Enterprise WeChat department to the business department code before writing the policy.

The mapping target is the stable business department code and name, for example:

- Enterprise WeChat `中心四部（男装）` maps to business department `6010102 / 中心四部(男装)`.

The mapping layer should support aliases so naming differences do not create empty scopes. Known examples from current data:

- `中心B部(超市)` maps to `6010104 / 中心BF部(超市)`.
- `中心B部(生鲜)` maps to `6010106 / 中心BF部(生鲜)`.
- `中心五部(运动)` maps to `6010118 / 中心五部(运休)`.
- `中心市场部--营运` maps to `6010110 / 中心营运部`.
- `中心市场部--客服` maps to `6010109 / 中心企划客服部`.
- `中心市场部--企划` maps to `6010108 / 中心企划执行部`.
- `大楼营运` maps to `6020111 / 营运四部`.

The implementation can start with a small explicit alias table or configuration file, then fall back to exact normalized name matching against active business departments.

## Flow

### Enterprise WeChat Login

1. User authorizes through Enterprise WeChat.
2. ShopView resolves the Enterprise WeChat identity to `users.user_id`.
3. ShopView obtains the user's Enterprise WeChat department from the existing contact sync data or by fetching the member profile if needed.
4. ShopView maps the Enterprise WeChat department to a business department code.
5. ShopView upserts the auto `business_scope/view` policy for the user.
6. Login continues even if the scope refresh fails, but the failure is logged with enough context for an administrator to repair the mapping.

### Contact Sync

The existing Enterprise WeChat contact sync should also refresh auto department scopes. This covers department changes and users who do not trigger login immediately after a sync.

The sync should:

1. Resolve the user's one Enterprise WeChat department.
2. Map it to a business department code.
3. Replace only the user's auto department policy.
4. Preserve manual policies and role assignments.

## Authorization Behavior

Existing API authorization should continue to call `load_business_scope(...)`. The desired effective scope is:

- automatic Enterprise WeChat department range, plus
- manually added extra ranges.

Current `load_business_scope(...)` loads active user policies with `source_type = WECOM` and `source_system = wecom`. During implementation, confirm whether manual extra ranges are currently visible to `load_business_scope(...)`. If they are filtered out, adjust the loader or manual policy marker so automatic and manual ranges combine without granting unintended role-level access.

## Error Handling

Missing or ambiguous mapping should not grant access. The system should log a diagnostic record with:

- user id
- real name
- Enterprise WeChat user id
- Enterprise WeChat department name
- failure reason

The admin-facing repair path is to add or correct the department mapping, then rerun the sync for that user or the full contact sync.

## Validation

Implementation should include focused tests or diagnostic scripts for these cases:

1. Jiang Jiawei receives `department:6010102` from Enterprise WeChat department `中心四部(男装)` and can see scoped business data.
2. Existing manual extra ranges remain after automatic scope refresh.
3. A missing department mapping creates no data policy and records a diagnostic failure.
4. Alias examples such as `中心B部(超市)` and `中心五部(运动)` resolve to the correct business department codes.
5. Contact sync refreshes automatic scopes without deleting non-auto policies.

## Rollout

1. Add mapping and upsert logic in code.
2. Run dry-run diagnostics against current production data to list users whose Enterprise WeChat departments map successfully or fail.
3. Apply the auto-scope refresh for matched users.
4. Verify Jiang Jiawei and several department-manager samples through admin view mode.
5. Review unresolved mappings and add aliases before broad launch.
