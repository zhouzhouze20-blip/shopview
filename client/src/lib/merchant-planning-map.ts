export type MerchantCandidateType = "VACANT" | "LOW_EFFICIENCY" | "EXPIRING" | "NORMAL";

export type CandidateMapStyle = {
  fill: string;
  stroke: string;
  text: string;
};

const CANDIDATE_TYPE_TEXT: Record<MerchantCandidateType, string> = {
  VACANT: "空置",
  LOW_EFFICIENCY: "低效",
  EXPIRING: "到期",
  NORMAL: "普通",
};

const CANDIDATE_MAP_STYLES: Record<MerchantCandidateType, CandidateMapStyle> = {
  VACANT: {
    fill: "rgba(14,165,233,0.58)",
    stroke: "rgba(3,105,161,0.92)",
    text: "rgb(7,89,133)",
  },
  LOW_EFFICIENCY: {
    fill: "rgba(244,63,94,0.54)",
    stroke: "rgba(190,18,60,0.94)",
    text: "rgb(159,18,57)",
  },
  EXPIRING: {
    fill: "rgba(245,158,11,0.58)",
    stroke: "rgba(180,83,9,0.94)",
    text: "rgb(146,64,14)",
  },
  NORMAL: {
    fill: "rgba(226,232,240,0.34)",
    stroke: "rgba(100,116,139,0.65)",
    text: "rgb(71,85,105)",
  },
};

export function candidateTypeText(type?: string | null) {
  return CANDIDATE_TYPE_TEXT[(type || "NORMAL") as MerchantCandidateType] ?? CANDIDATE_TYPE_TEXT.NORMAL;
}

export function candidateMapStyle(type?: string | null, selected = false): CandidateMapStyle {
  const base = CANDIDATE_MAP_STYLES[(type || "NORMAL") as MerchantCandidateType] ?? CANDIDATE_MAP_STYLES.NORMAL;
  if (!selected) return base;
  return {
    fill: "rgba(59,130,246,0.62)",
    stroke: "rgba(37,99,235,1)",
    text: "rgb(30,64,175)",
  };
}
