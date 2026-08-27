import crown from "../../assets/golden_crown.svg";
import trumpet from "../../assets/golden_trump.svg";
import melkovHead from "../../assets/melkov_head.svg";

interface HeaderProps {
  title?: string;
  subtitle?: string;
}

export function Header({ title = "Aegis Art Atelier", subtitle = "AI Art Expert Agent" }: HeaderProps) {
  return (
    <header className="masthead panel">
      <div className="masthead-side">
        <img className="crest" src={crown} alt="" aria-hidden="true" />
        <div>
          <p className="small-label">HOUSE OF VALTORIA</p>
          <p className="small-subtitle">The Court of Melkov</p>
        </div>
      </div>

      <div className="masthead-center">
        <span className="masthead-rule" aria-hidden="true" />
        <div className="ornament ornament-left" aria-hidden="true">
          <img src={trumpet} alt="" />
        </div>
        <div>
          <h1>{title}</h1>
          <p>{subtitle}</p>
        </div>
        <div className="ornament ornament-right" aria-hidden="true">
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
