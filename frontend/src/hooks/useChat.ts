import { useCallback, useMemo, useRef } from "react";
import { readArtwork } from "../services/artwork.service";
import { ChatError, clearSession, sendChatMessage } from "../services/chat.service";
import { getSessionId, resetSessionId } from "../services/session.service";
import { useAnalysisStore } from "../stores/analysis.store";
import { useArtworkStore } from "../stores/artwork.store";
import { useChatStore } from "../stores/chat.store";
import { TOOL_NAMES, type ChatResponseBody } from "../types/api";
import { MELKOV_NAME, VISITOR_NAME } from "../utils/constant";
import { stripDataUrlPrefix, toDataUrl } from "../utils/image";

/**
 * Drives one conversational turn against POST /chat.
 *
 * Everything the panels display originates here: the reply text, the tools
 * the agent reached for, the FLUX image, the MET records, and the curatorial
 * passage. Nothing is synthesised — where the backend returns no data the
 * corresponding store stays null and its panel shows an empty state.
 */
export function useChat() {
  const { messages, status, error, addMessage, setStatus, setError, resetChat } =
    useChatStore();
  const sessionId = useMemo(() => getSessionId(), []);
  // The image this session has already uploaded, so it is sent once rather
  // than with every message. Cleared when the consultation resets.
  const sentImageRef = useRef<string | null>(null);
  // The upload-time read in flight, if any, keyed by the image it is reading.
  // A turn sent while it runs waits for it rather than racing the Space.
  const primingRef = useRef<{ image: string; promise: Promise<boolean> } | null>(null);
  // The image last shown inside a user bubble. The artwork stays in the frame
  // for the whole consultation, so the thumbnail appears once, on the first
  // message about it, and not again on every later question.
  const shownImageRef = useRef<string | null>(null);

  /**
   * Read the artwork in the frame before the first question about it.
   *
   * Called when the visitor starts typing — intent, not the drop itself, so
   * a picture hung and replaced never wakes the GPU Space, and the daily
   * quota goes only to images someone is about to ask about. The backend
   * caches by image hash, so this never runs a model twice for one image.
   * On success the image counts as sent, and the confidence and reading
   * panels fill before the question is even finished.
   */
  const primeArtwork = useCallback(() => {
    const attachment = useArtworkStore.getState().imageBase64;
    if (
      attachment === null ||
      attachment === sentImageRef.current ||
      primingRef.current?.image === attachment ||
      status === "thinking" ||
      status === "analyzing"
    ) {
      return;
    }

    useArtworkStore.getState().setStatus("analyzing");
    const promise = readArtwork({ session_id: sessionId, image_base64: attachment })
      .then((reading) => {
        sentImageRef.current = attachment;
        useAnalysisStore.getState().setReading({
          text: reading.vlm_description,
          source: "Qwen2.5-VL-7B · fine-tuned",
        });
        if (reading.style_analysis) {
          useAnalysisStore.getState().setStyles(
            reading.style_analysis.predictions.map((prediction) => ({
              label: prediction.label,
              score: prediction.probability,
            })),
          );
        }
        return true;
      })
      // A failed read is not an error the visitor needs to see: the image
      // simply travels with the next turn, as it did before this existed.
      .catch(() => false)
      .finally(() => {
        if (primingRef.current?.image === attachment) {
          primingRef.current = null;
        }
        const current = useArtworkStore.getState();
        if (current.status === "analyzing" && current.imageBase64 === attachment) {
          current.setStatus("ready");
        }
      });
    primingRef.current = { image: attachment, promise };
  }, [sessionId, status]);

  const sendMessage = useCallback(
    async (text: string) => {
      const message = text.trim();
      if (!message || status === "thinking" || status === "analyzing") {
        return;
      }

      const artwork = useArtworkStore.getState();
      const attachment = artwork.imageBase64;

      // If the upload-time read is still running for this very image, let it
      // finish: the turn then finds the description cached and skips the
      // Space entirely, instead of a second call queuing behind the first.
      if (attachment !== null && primingRef.current?.image === attachment) {
        setStatus("analyzing");
        await primingRef.current.promise;
      }

      // The frame keeps the artwork, so every turn would otherwise re-upload
      // the same megabytes to tell the backend something it already knows.
      // The backend treats "no image, but a reading cached for this session"
      // as the same artwork still being in the frame, so silence is enough —
      // and a genuinely new upload still travels, because it differs from
      // what was sent last.
      const alreadySent = attachment !== null && attachment === sentImageRef.current;
      const outgoingImage = alreadySent ? null : attachment;

      const firstMessageAboutImage = attachment !== null && attachment !== shownImageRef.current;
      addMessage({
        role: "user",
        name: VISITOR_NAME,
        content: message,
        attachment: firstMessageAboutImage ? attachment : null,
      });
      shownImageRef.current = attachment;

      // A turn carrying image bytes will very likely route to the VLM Space,
      // which cold-starts; the panel says "examining" rather than "thinking"
      // so the longer wait reads as deliberate rather than broken. An image
      // already read at upload time costs no such wait, so it just "thinks".
      setStatus(outgoingImage ? "analyzing" : "thinking");
      setError(null);
      if (outgoingImage) {
        useArtworkStore.getState().setStatus("analyzing");
      }

      try {
        const response = await sendChatMessage({
          message,
          session_id: sessionId,
          image_base64: outgoingImage,
        });
        // Recorded only after the turn succeeds: a failed request never
        // reached the backend, so the image still needs sending next time.
        sentImageRef.current = attachment;

        addMessage({
          role: "assistant",
          name: MELKOV_NAME,
          content: response.reply,
          tools: response.tools_used,
          generatedImage: response.generated_image_base64,
          metResults: response.met_results,
          louvreResults: response.louvre_results,
          britishMuseumResults: response.british_museum_results,
          artAdvice: response.art_advice,
        });
        setStatus("idle");
        applyArtifacts(response);
      } catch (failure) {
        const chatError =
          failure instanceof ChatError
            ? failure
            : new ChatError("Melkov could not complete that consultation.");
        addMessage({
          role: "assistant",
          name: MELKOV_NAME,
          content: chatError.message,
          failed: true,
        });
        setError(chatError.message);
      } finally {
        const current = useArtworkStore.getState();
        if (current.status === "analyzing") {
          current.setStatus(current.previewUrl ? "ready" : "empty");
        }
      }
    },
    [addMessage, sessionId, setError, setStatus, status],
  );

  const startNewConsultation = useCallback(async () => {
    await clearSession(getSessionId());
    resetSessionId();
    // The new session's backend cache is empty, so the next image must travel.
    sentImageRef.current = null;
    primingRef.current = null;
    shownImageRef.current = null;
    resetChat();
    useAnalysisStore.getState().resetAnalysis();
    useArtworkStore.getState().clearArtwork();
  }, [resetChat]);

  return {
    messages,
    status,
    error,
    sessionId,
    busy: status === "thinking" || status === "analyzing",
    sendMessage,
    primeArtwork,
    startNewConsultation,
  };
}

/**
 * Route a finished turn's artifacts into the panels that display them.
 *
 * @param response The finished turn, straight from the backend.
 */
function applyArtifacts(response: ChatResponseBody): void {
  const { reply, tools_used: tools, generated_image_base64: generatedImage } = response;

  // The vision model's own words, kept verbatim for the observations panel.
  // Only replaced when this turn actually produced one, so an unrelated
  // follow-up question does not wipe the reading of the artwork on screen.
  if (response.vlm_description) {
    useAnalysisStore.getState().setReading({
      text: response.vlm_description,
      source: "Qwen2.5-VL-7B \u00b7 fine-tuned",
    });
  }

  // The style classifier's ranking fills the confidence panel. Mapped from
  // the wire's `probability` to the chart's `score`, and only when this turn
  // actually classified something — otherwise a follow-up question would
  // blank the scores for the artwork still on screen.
  if (response.style_analysis) {
    useAnalysisStore.getState().setStyles(
      response.style_analysis.predictions.map((prediction) => ({
        label: prediction.label,
        score: prediction.probability,
      })),
    );
  }

  // A generated image becomes the artwork in the frame, so the visitor can
  // immediately ask Melkov to critique what he just painted.
  if (generatedImage) {
    useArtworkStore.getState().placeArtwork({
      imageBase64: stripDataUrlPrefix(generatedImage),
      previewUrl: toDataUrl(generatedImage),
      generated: true,
    });
  }

  // When the agent consulted the art-history corpus, this turn's reply is a
  // grounded curatorial passage and belongs in the archive panel. The tool's
  // own query is the only reference the backend exposes, so it is shown as
  // the reference rather than a fabricated catalogue number.
  const historyCall = tools.find((call) => call.tool === TOOL_NAMES.history);
  if (historyCall) {
    useAnalysisStore.getState().setHistory({
      content: reply,
      citation: {
        source: "Art History Corpus",
        referenceId: historyCall.input_summary || null,
      },
    });
  }
}
