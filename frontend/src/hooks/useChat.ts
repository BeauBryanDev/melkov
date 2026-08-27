import { useCallback, useMemo, useRef } from "react";
import { ChatError, clearSession, sendChatMessage } from "../services/chat.service";
import { getSessionId, resetSessionId } from "../services/session.service";
import { useAnalysisStore } from "../stores/analysis.store";
import { useArtworkStore } from "../stores/artwork.store";
import { useChatStore } from "../stores/chat.store";
import { TOOL_NAMES, type ChatResponseBody } from "../types/api";
import { MELKOV_NAME, VISITOR_NAME } from "../utils/constant";
import { stripDataUrlPrefix, toDataUrl } from "../utils/image";

/**
 * Drives one conversational turn against `POST /chat`.
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

  const sendMessage = useCallback(
    async (text: string) => {
      const message = text.trim();
      if (!message || status === "thinking" || status === "analyzing") {
        return;
      }

      const artwork = useArtworkStore.getState();
      const attachment = artwork.imageBase64;

      // The frame keeps the artwork, so every turn would otherwise re-upload
      // the same megabytes to tell the backend something it already knows.
      // The backend treats "no image, but a reading cached for this session"
      // as the same artwork still being in the frame, so silence is enough —
      // and a genuinely new upload still travels, because it differs from
      // what was sent last.
      const alreadySent = attachment !== null && attachment === sentImageRef.current;
      const outgoingImage = alreadySent ? null : attachment;

      addMessage({
        role: "user",
        name: VISITOR_NAME,
        content: message,
        attachment,
      });

      // A turn carrying an image will very likely route to the VLM Space,
      // which cold-starts; the panel says "examining" rather than "thinking"
      // so the longer wait reads as deliberate rather than broken.
      setStatus(attachment ? "analyzing" : "thinking");
      setError(null);
      if (attachment) {
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
