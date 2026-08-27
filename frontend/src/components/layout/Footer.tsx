interface FooterProps {
  left?: string;
  right?: string;
}

export function Footer({ left = "Aegis Art Atelier", right = "Curated by Melkov" }: FooterProps) {
  return (
    <footer className="footerbar panel">
      <span>{left}</span>
      <span>{right}</span>
    </footer>
  );
}
