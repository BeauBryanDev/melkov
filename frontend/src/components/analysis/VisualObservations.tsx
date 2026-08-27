import type { VisualObservation, VlmReading } from "../../types/rag";
import { Panel } from "../ui/Panel";
import { EmptyState } from "../common/EmptyState";

interface VisualObservationsProps {
  /** The vision model's verbatim reading of the artwork. */
  reading: VlmReading | null;
  /** Labelled observations, once the backend produces them. */
  observations: VisualObservation[] | null;
}

/**
 * What Melkov sees on the picture surface, as distinct from what he knows
 * about its history (FRONTEND_SPEC §23).
 *
 * The prose comes straight from the fine-tuned Qwen2.5-VL, carried through
 * `ChatResponse.vlm_description`. It is shown **verbatim**, not parsed into
 * LIGHT / COLOUR / BRUSHWORK rows: the model returns one block of prose, and
 * splitting it here would be the frontend asserting a structure the model
 * never produced. It is also the one place in the interface showing the
 * vision model's own words rather than the orchestrator's paraphrase — which
 * matters, since the orchestrator cannot see the image at all.
 *
 * The labelled `observations` list renders above the prose if the backend
 * ever starts returning real fields; until then it is simply absent.
 */
export function VisualObservations({ reading, observations }: VisualObservationsProps) {
  const hasObservations = Boolean(observations && observations.length > 0);

  return (
    <Panel className="observations-panel max-sm:p-2.5">
      <div className="panel-title panel-title-row">
        <h2>Visual Observations</h2>
      </div>

      {hasObservations || reading ? (
        <div className="observation-content">
          {hasObservations ? (
            <dl className="observation-list">
              {observations!.map((observation) => (
                <div className="observation-row" key={observation.label}>
                  <dt className="metadata-label">{observation.label}</dt>
                  <dd>{observation.value}</dd>
                </div>
              ))}
            </dl>
          ) : null}

          {reading ? (
            <section className="vlm-reading">
              <p className="metadata-label">Melkov&rsquo;s reading</p>
              <div className="vlm-reading-body">
                {reading.text
                  .split(/\n{2,}/)
                  .map((paragraph) => paragraph.trim())
                  .filter(Boolean)
                  .map((paragraph, index) => (
                    // eslint-disable-next-line react/no-array-index-key
                    <p key={index}>{paragraph}</p>
                  ))}
              </div>
              <p className="vlm-reading-source">Source: {reading.source}</p>
            </section>
          ) : null}
        </div>
      ) : (
        <EmptyState
          title="Nothing observed yet"
          body="Hang a painting in the frame and ask Melkov about it. What his eye reports will be recorded here, in his own words."
        />
      )}
    </Panel>
  );
}
