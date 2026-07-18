export type GovernanceErrorCode =
  | "BASELINE_INVALID"
  | "TEMPO_CHECKOUT_MISSING"
  | "TEMPO_CHECKOUT_DRIFT"
  | "TEMPO_CHECKOUT_DIRTY"
  | "TEMPO_ORIGIN_MISMATCH"
  | "TEMPO_COMMAND_FAILED"
  | "TEMPO_RESPONSE_INVALID"
  | "GOVERNANCE_ROOT_MISSING"
  | "LEDGER_INVALID"
  | "WARRANT_MISSING"
  | "WARRANT_INVALID"
  | "WARRANT_EXPIRED"
  | "WARRANT_REVOKED"
  | "START_RECEIPT_MISSING"
  | "START_SCOPE_MISMATCH"
  | "RECEIPT_INVALID"
  | "RECEIPT_TAMPERED"
  | "BOUND_ARTIFACT_TAMPERED";

export class GovernanceError extends Error {
  readonly code: GovernanceErrorCode;

  constructor(code: GovernanceErrorCode, message: string) {
    super(message);
    this.name = "GovernanceError";
    this.code = code;
  }
}
