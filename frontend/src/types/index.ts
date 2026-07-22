export interface AgentFindingResponse {
  clause_id: string;
  risk_level: string;
  confidence: number;
  rationale: string;
  cited_evidence_ids: string[];
  policy_refs: string[];
}

export interface RedlineSuggestionResponse {
  clause_id: string;
  original_text: string;
  suggested_text: string;
  rationale: string;
  executive_summary: string;
}

export interface PolicyRuleResultResponse {
  rule_id: string;
  description: string;
  action: string;
}

export interface PolicyDecisionResponse {
  finding_id: string;
  clause_id: string;
  original_risk_level: string;
  original_confidence: number;
  final_risk_level: string;
  requires_human_review: boolean;
  rules_fired: PolicyRuleResultResponse[];
  decision_id: string;
}

export interface Clause {
  contract_id: string;
  text: string;
  clause_id: string;
  clause_type_guess?: string;
  start_offset: number;
  end_offset: number;
}

export interface PipelineResultResponse {
  contract_id: string;
  clauses_processed: number;
  findings: AgentFindingResponse[];
  redlines: RedlineSuggestionResponse[];
  flagged_for_review: string[];
  policy_decisions: PolicyDecisionResponse[];
  warnings: string[];
  all_clauses: Clause[];
  processing_time_ms: number;
}
