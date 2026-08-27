import type { StylePrediction } from "../../types/rag";
import { Panel } from "../ui/Panel";
import { ConfidenceBar } from "./ConfidenceBar";
import { EmptyState } from "../common/EmptyState";
import { confidenceBand, formatScore } from "../../utils/format";

interface ConfidenceChartProps {
  title?: string;
  styles: StylePrediction[] | null;
}

/**
 * Style classification, with the winning label given the weight
 * (FRONTEND_SPEC §21–§22).
 *
 * `styles` is null until a turn actually classifies an image — the panel
 * shows its empty state rather than the 82% Impressionism figure the mockup
 * illustrates, which is a design example and not data.
 *
 * The backend returns only the top 3 of 15 classes, so the ranking does not
 * sum to 1. The shortfall is shown as a single "Other" row, exactly as the
 * mockup does: without it the bars look like they are hiding something.
 */
export function ConfidenceChart({ title = "Style Analysis", styles }: ConfidenceChartProps) {
  const ranked = styles ? [...styles].sort((a, b) => b.score - a.score) : [];
  const [primary, ...alternatives] = ranked;

  // Rounded to the same precision the bars are drawn at, so a residue too
  // small to see (0.4% and under) does not add an "Other 0%" row.
  const remainder = ranked.reduce((total, style) => total - style.score, 1);
  const showRemainder = remainder >= 0.005;

  return (
    <Panel className="confidence-panel max-sm:p-2.5">
      <div className="panel-title panel-title-row">
        <h2>{title}</h2>
      </div>

      {primary ? (
        <div className="confidence-chart">
          <div className="confidence-primary">
            <p className="metadata-label">Primary style</p>
            <p className="confidence-primary-label">{primary.label}</p>
            <p className="confidence-primary-score">{formatScore(primary.score)}</p>
            <p className="confidence-primary-band">{confidenceBand(primary.score)}</p>
          </div>

          <div className="confidence-body">
            <ConfidenceBar label={primary.label} score={primary.score} primary />
            {alternatives.length > 0 || showRemainder ? (
              <>
                <p className="metadata-label confidence-divider">Alternative classifications</p>
                {alternatives.map((style) => (
                  <ConfidenceBar key={style.label} label={style.label} score={style.score} />
                ))}
                {showRemainder ? <ConfidenceBar label="Other" score={remainder} /> : null}
              </>
            ) : null}
          </div>

          <div className="confidence-axis" aria-hidden="true">
            <span>0%</span>
            <span>25%</span>
            <span>50%</span>
            <span>75%</span>
            <span>100%</span>
          </div>
        </div>
      ) : (
        <EmptyState
          title="No classification yet"
          body="Style scoring will appear here once the analysis returns a classification."
        />
      )}
    </Panel>
  );
}
