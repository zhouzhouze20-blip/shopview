import assert from "node:assert/strict";
import test from "node:test";
import { filterAdminViewUsers, getNextAdminViewSearchState } from "./admin-view-search.ts";

const users = [
  { user_id: 1, username: "admin", real_name: "系统管理员", employee_no: "A001" },
  { user_id: 2, username: "shenlei", real_name: "沈磊", employee_no: "S002" },
  { user_id: 3, username: "zhangsan", real_name: "张三", employee_no: "Z003" },
];

test("keeps the previous admin-view keyword while showing IME composition text", () => {
  assert.deepEqual(
    getNextAdminViewSearchState({
      currentKeyword: "",
      inputValue: "s",
      isComposing: true,
    }),
    { inputText: "s", keyword: "" },
  );
});

test("commits the admin-view keyword after an IME composition finishes", () => {
  assert.deepEqual(
    getNextAdminViewSearchState({
      currentKeyword: "",
      inputValue: "沈",
      isComposing: false,
    }),
    { inputText: "沈", keyword: "沈" },
  );
});

test("filters admin-view users by username, real name, or employee number", () => {
  assert.deepEqual(
    filterAdminViewUsers(users, "shen").map((user) => user.user_id),
    [2],
  );
  assert.deepEqual(
    filterAdminViewUsers(users, "沈").map((user) => user.user_id),
    [2],
  );
  assert.deepEqual(
    filterAdminViewUsers(users, "Z003").map((user) => user.user_id),
    [3],
  );
});
