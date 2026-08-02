import { useCallback, useEffect, useRef } from "react";

import { apiPost } from "@/lib/api";

export type ModuleQueryConditions = Record<
  string,
  string | number | boolean | Array<string | number> | null | undefined
>;

type ModuleAccessLogOptions = {
  moduleId: string;
  moduleName: string;
  enabled?: boolean;
  clientType?: "mobile" | "desktop";
  initialQueryConditions?: ModuleQueryConditions;
};

export function useModuleAccessLog({
  moduleId,
  moduleName,
  enabled = true,
  clientType,
  initialQueryConditions,
}: ModuleAccessLogOptions) {
  const loggedRef = useRef(false);

  const postLog = useCallback((actionCode: "enter" | "query", queryConditions?: ModuleQueryConditions) => {
    if (!enabled) return;
    void apiPost("/api/system/module-access-log", {
      module_id: moduleId,
      module_name: moduleName,
      client_type: clientType,
      path: window.location.pathname,
      action_code: actionCode,
      query_conditions: queryConditions,
    }).catch(() => {
      // 审计日志失败不阻断用户进入模块或执行查询。
    });
  }, [clientType, enabled, moduleId, moduleName]);

  useEffect(() => {
    if (!enabled || loggedRef.current) return;
    loggedRef.current = true;
    postLog("enter");
    if (initialQueryConditions) postLog("query", initialQueryConditions);
  }, [enabled, initialQueryConditions, postLog]);

  const recordQuery = useCallback((queryConditions: ModuleQueryConditions) => {
    postLog("query", queryConditions);
  }, [postLog]);

  return { recordQuery };
}
