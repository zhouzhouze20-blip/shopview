export interface AdminViewSearchUser {
  user_id: number;
  username: string;
  real_name?: string | null;
  employee_no?: string | null;
}

export function getNextAdminViewSearchState({
  currentKeyword,
  inputValue,
  isComposing,
}: {
  currentKeyword: string;
  inputValue: string;
  isComposing: boolean;
}): { inputText: string; keyword: string } {
  return {
    inputText: inputValue,
    keyword: isComposing ? currentKeyword : inputValue,
  };
}

export function filterAdminViewUsers<T extends AdminViewSearchUser>(users: T[], keyword: string): T[] {
  const normalizedKeyword = keyword.trim().toLowerCase();
  if (!normalizedKeyword) return users;

  return users.filter((candidate) =>
    [candidate.username, candidate.real_name, candidate.employee_no]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(normalizedKeyword)),
  );
}
