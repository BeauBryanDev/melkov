interface FooterProps {
  left?: string;
  right?: string;
}

export function Footer({ left = "Aegis Art Atelier", right = "Curated by Melkov" }: FooterProps) {
  return (
    <footer className="footerbar panel">
      <span>{left} MELKOV ART ATELIER</span>
      <span>{right}ART AGENT POWERED BY CLAUDE-SONNET AND QWEN-2.5-VL-7B</span>
    </footer>
  );
}
