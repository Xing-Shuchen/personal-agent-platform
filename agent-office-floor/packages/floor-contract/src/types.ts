export type FloorId = string;
export type TimestampMs = number;
export type FloorStatus =
  | "running"
  | "waiting_input"
  | "error"
  | "completed"
  | "idle"
  | "queued"
  | "stopped"
  | "unknown";
export type WorkPhase =
  | "executing"
  | "reading"
  | "thinking"
  | "finishing"
  | "waiting_child"
  | null;
export type Freshness = "fresh" | "stale" | "unknown";
export type CapabilityState =
  | "available"
  | "partial"
  | "unsupported"
  | "forbidden"
  | "unverified";
export type CapabilityName =
  | "sessionList"
  | "sessionEvents"
  | "runEvents"
  | "toolEvents"
  | "blockingInput"
  | "progressCard"
  | "compaction"
  | "loopDetection"
  | "handoff";
export interface ObservationEvidence {
  readonly source:
    | "session_snapshot"
    | "session_delta"
    | "run_event"
    | "tool_event"
    | "input_event"
    | "operation_event"
    | "progress_card";
  readonly reference: string;
  readonly sourceAtMs: TimestampMs | null;
  readonly observedAtMs: TimestampMs;
}
export interface InputAttention {
  readonly id: string;
  readonly kind: "question" | "approval";
  readonly runId: string | null;
  readonly blocking: boolean | null;
  readonly label: string;
}
export interface RunOutcome {
  readonly runId: string | null;
  readonly result: "success" | "error" | "cancelled" | "timeout";
  readonly endedAtMs: TimestampMs | null;
  readonly message: string | null;
}
export interface FloorProgress {
  readonly revision: number;
  readonly updatedAtMs: TimestampMs;
  readonly markdown: string | null;
  readonly steps: readonly {
    readonly text: string;
    readonly status: "pending" | "in_progress" | "completed";
  }[] | null;
}
export interface FloorAgent {
  readonly id: FloorId;
  readonly session: {
    readonly gatewayId: string;
    readonly key: string;
    readonly agentId: string | null;
    readonly sessionId: string | null;
  };
  readonly name: string;
  readonly kind: string | null;
  readonly avatarKey: string;
  readonly relation: {
    readonly parentId: FloorId | null;
    readonly childIds: readonly FloorId[] | null;
    readonly runningVisibleChildren: number | null;
  };
  readonly work: {
    readonly status: FloorStatus;
    readonly phase: WorkPhase;
    readonly hasActiveRun: boolean | null;
    readonly activeRunIds: readonly string[] | null;
    readonly tool: {
      readonly name: string;
      readonly callId: string | null;
      readonly phase: "start" | "update" | "end";
    } | null;
    readonly attention: readonly InputAttention[] | null;
    readonly compacting: boolean | null;
    readonly looping: boolean | null;
    readonly latestOutcome: RunOutcome | null;
    readonly summary: string | null;
    readonly summarySource:
      | "tool"
      | "narration"
      | "progress_card"
      | "visible_message"
      | null;
    readonly evidence: readonly ObservationEvidence[];
  };
  readonly model: {
    readonly selected: string | null;
    readonly selectedProvider: string | null;
    readonly active: string | null;
    readonly activeProvider: string | null;
  };
  readonly usage: {
    readonly inputTokens: number | null;
    readonly outputTokens: number | null;
    readonly totalTokens: number | null;
    readonly totalTokensFresh: boolean | null;
    readonly contextTokens: number | null;
  };
  readonly progress: FloorProgress | null;
  readonly lastMessagePreview: string | null;
  readonly metadataUpdatedAtMs: TimestampMs | null;
  readonly lastActivityAtMs: TimestampMs | null;
  readonly lastInteractionAtMs: TimestampMs | null;
  readonly lastVerifiedAtMs: TimestampMs | null;
  readonly freshness: Freshness;
}
export interface FloorHandoff {
  readonly id: string;
  readonly fromId: FloorId;
  readonly toId: FloorId;
  readonly kind: "request" | "result" | "message";
  readonly observedAtMs: TimestampMs;
  readonly expiresAtMs: TimestampMs;
  readonly evidenceReference: string;
}
export interface FloorConnection {
  readonly mode: "subscription" | "polling" | "none";
  readonly state:
    | "connecting"
    | "live"
    | "degraded"
    | "offline"
    | "auth_required";
  readonly lastConfirmedAtMs: TimestampMs | null;
  readonly reason: string | null;
}
export interface FloorState {
  readonly schemaVersion: 1;
  readonly epoch: string;
  readonly revision: number;
  readonly generatedAtMs: TimestampMs;
  readonly connection: FloorConnection;
  readonly capabilities: Readonly<
    Record<CapabilityName, CapabilityState>
  >;
  readonly agents: Readonly<Record<FloorId, FloorAgent>>;
  readonly handoffs: readonly FloorHandoff[];
}
export type FloorUpdate =
  | {
      readonly type: "snapshot";
      readonly state: FloorState;
    }
  | {
      readonly type: "patch";
      readonly schemaVersion: 1;
      readonly epoch: string;
      readonly baseRevision: number;
      readonly revision: number;
      readonly generatedAtMs: TimestampMs;
      readonly upserts: readonly FloorAgent[];
      readonly removeIds: readonly FloorId[];
      readonly connection?: FloorConnection;
      readonly capabilities?: FloorState["capabilities"];
      readonly handoffs?: readonly FloorHandoff[];
    };
