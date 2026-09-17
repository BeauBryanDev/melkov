import { TOOL_NAMES, type ToolCallLog } from "../../types/api";

interface ToolTraceProps {
  tools: ToolCallLog[];
}

/** Human wording for the agent's skills. */
const LABELS: Record<string, string> = {
  [TOOL_NAMES.describe]: "Examined the canvas",
  [TOOL_NAMES.generate]: "Painted a new work",
  [TOOL_NAMES.met]: "Consulted the Met collection",
  [TOOL_NAMES.louvre]: "Consulted the Louvre",
  [TOOL_NAMES.britishMuseum]: "Consulted the British Museum",
  [TOOL_NAMES.cleveland]: "Consulted the Cleveland Museum of Art",
  [TOOL_NAMES.gallery]: "Searched his own gallery",
  [TOOL_NAMES.advice]: "Found studio lessons",
  [TOOL_NAMES.history]: "Consulted the art-history library",
};

/**
 * Which skills produced this reply.
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
