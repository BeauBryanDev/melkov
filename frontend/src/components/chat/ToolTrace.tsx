import { TOOL_NAMES, type ToolCallLog } from "../../types/api";

interface ToolTraceProps {
  tools: ToolCallLog[];
}

/** Human wording for each of the agent's four skills. */
const LABELS: Record<string, string> = {
  [TOOL_NAMES.describe]: "Examined the canvas",
  [TOOL_NAMES.generate]: "Painted a new work",
  [TOOL_NAMES.met]: "Consulted the Met collection",
  [TOOL_NAMES.history]: "Consulted the art-history library",
};

/**
 * Which skills produced this reply.
 *
 * Shown because it is the visitor's evidence that a remark about the picture
 * came from Melkov's trained eye rather than from prose alone — the
 * orchestrator never sees the attachment, so "Examined the canvas" is a real
 * guarantee, not decoration.
 */
export function ToolTrace({ tools }: ToolTraceProps) {
  const labels = Array.from(
    new Set(tools.map((call) => LABELS[call.tool]).filter(Boolean)),
  );

  if (labels.length === 0) {
    return null;
  }

  return (
    <ul className="tool-trace">
      {labels.map((label) => (
        <li key={label}>{label}</li>
      ))}
    </ul>
  );
}
