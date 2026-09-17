import { VisualObservations } from "./components/analysis/VisualObservations";
import { ArtworkFrame } from "./components/artwork/ArtworkFrame";
import { ChatPanel } from "./components/chat/ChatPanel";
import { ConfidenceChart } from "./components/confidence/ConfidenceChart";
import { ArtHistoryPanel } from "./components/history/ArtHistoryPanel";
import { Footer } from "./components/layout/Footer";
import { Header } from "./components/layout/Header";
import { MainLayout } from "./components/layout/MainLayout";
import { useArtwork } from "./hooks/useArtwork";
import { useChat } from "./hooks/useChat";
import { useAnalysisStore } from "./stores/analysis.store";

/**
 * The atelier.
 *
 */
function App() {
  const artwork = useArtwork();
  const chat = useChat();
  const { styles, observations, history, reading } = useAnalysisStore();

  return (
    <MainLayout header={<Header />} footer={<Footer />}>
      <main className="dashboard-grid">
        <ArtworkFrame
          analysis={artwork.analysis}
          error={artwork.error}
          fileName={artwork.fileName}
          generated={artwork.generated}
          imageBase64={artwork.imageBase64}
          onClear={artwork.clearArtwork}
          onFile={artwork.acceptFile}
          previewUrl={artwork.previewUrl}
          status={artwork.status}
        />

        <ChatPanel
          busy={chat.busy}
          hasArtwork={Boolean(artwork.previewUrl)}
          messages={chat.messages}
          onFile={artwork.acceptFile}
          onNewConsultation={chat.startNewConsultation}
          onSend={chat.sendMessage}
          status={chat.status}
        />

        <VisualObservations observations={observations} reading={reading} />

        <ConfidenceChart styles={styles} />

        <ArtHistoryPanel entry={history} />
      </main>
    </MainLayout>
  );
}

export default App;
