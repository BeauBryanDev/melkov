import crown from "../../assets/paint_pallette.svg";
import trumpet from "../../assets/golden_trump.svg";
import melkovHead from "../../assets/melkov_avatar.svg";
import paintBrush from "../../assets/painting_brush1.svg";

interface HeaderProps {
  title?: string;
  subtitle?: string;
}

export function Header({ title = "Melkov Art Atelier", subtitle = "AI Art Expert Agent" }: HeaderProps) {
  return (
    <header className="masthead panel">
      <div className="masthead-side">
        <img className="crest" src={crown} alt="" aria-hidden="true" />
        <div>
          <p className="small-label">ART ATELIER STUDIO</p>
          <p className="small-subtitle">The Golden Boy Studio</p>
        </div>
      </div>

      <div className="masthead-center">
        <span className="masthead-rule" aria-hidden="true" />
        <div className="ornament ornament-left" aria-hidden="true">
          <img className="ornament-brush" src={paintBrush} alt="" />
          <img src={trumpet} alt="" />
        </div>
        <div>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
        <div className="ornament ornament-right" aria-hidden="true">
          <img className="ornament-brush" src={paintBrush} alt="" />
          <img src={trumpet} alt="" />
        </div>
        <span className="masthead-rule" aria-hidden="true" />
      </div>

      <div className="masthead-side masthead-side-end">
        <div className="profile-copy">
          <p className="small-label">MELKOV</p>
          <p className="small-subtitle">AI Art Expert Agent</p>
        </div>
        <img className="profile-avatar" src={melkovHead} alt="" aria-hidden="true" />
      </div>
    </header>
  );
}
