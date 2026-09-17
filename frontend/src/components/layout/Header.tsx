import crown from "../../assets/paint_pallette.svg";
import trumpet from "../../assets/golden_trump.svg";
import melkovHead from "../../assets/melkov_avatar.svg";
import paintBrush from "../../assets/painting_brush1.svg";
import claudeLogo from "../../assets/claude_icon.png";
import hfLogo from "../../assets/HF_logo.png";
import qwenLogo from "../../assets/Qwen_Logo.png";
import fluxLogo from "../../assets/Flux_color_logo.png";
import metLogo from "../../assets/MET.png";
import pytorchLogo from "../../assets/pytorch-svgrepo-com.svg";
import nvidiaLogo from "../../assets/NVIDIA.png";
import bflLogo from "../../assets/black_forest_lab.svg";
import pythonLogo from "../../assets/Python.png";
import colabLogo from "../../assets/COLAB.png";
import NumpyIcon from "../../assets/Numpy.svg";
import FastAPI from "../../assets/FastAPI.svg";
import ReactIcon from "../../assets/React.svg";
import TS from "../../assets/TypeScript.svg";
import TailwindCSS  from "../../assets/Tailwindcss.svg"
import ViteIcon from "../../assets/Vite.svg";
import OpenCVIcon from "../../assets/OpenCV.svg";
import LangChainIcon from "../../assets/LangChain.png";


interface HeaderProps {
  title?: string;
  subtitle?: string;
}

/* The ML stack Melkov is built on, acknowledged in the masthead's two empty
   bands. `wordmark` marks the wide lockups (Qwen, FLUX) so they can be held to
   the same optical weight as the square icons rather than the same height. */
const LEFT_CREDITS = [
  { src: claudeLogo, name: "Claude" },
  { src: hfLogo, name: "Hugging Face" },
  { src: qwenLogo, name: "Qwen", wordmark: true },
  { src: nvidiaLogo, name: "NVIDIA" },
  { src: pytorchLogo, name: "PyTorch" },
  { src: NumpyIcon, name: "NumPy", wordmark: true },
  { src: pythonLogo, name: "Python" },
  { src: FastAPI, name: "FastAPI", wordmark: true },
  { src: OpenCVIcon, name: "OpenCV", wordmark: true },
  
];

const RIGHT_CREDITS = [
  
  { src: LangChainIcon, name: "LangChain" },
  { src: colabLogo, name: "Google Colab" },
  { src: bflLogo, name: "Black Forest Labs" },
  { src: fluxLogo, name: "FLUX", wordmark: true },
  { src: metLogo, name: "The Metropolitan Museum of Art" },
  { src: TailwindCSS, name: "TailwindCSS", wordmark: true },
  { src: ReactIcon, name: "React", wordmark: true },
  { src: TS, name: "TypeScript", wordmark: true },
  { src: ViteIcon, name: "Vite", wordmark: true },
];

export function Header({ title = "Melkov Art Atelier", subtitle = "AI Art Expert Agent" }: HeaderProps) {
  return (
    <header className="masthead panel">
      <div className="masthead-side">
        <img className="crest" src={crown} alt="" aria-hidden="true" />
        <div>
          <p className="small-label">ART ATELIER STUDIO</p>
          <p className="small-subtitle">The Golden Boy Studio</p>
        </div>
        <CreditStrip credits={LEFT_CREDITS} />
      </div>

      <div className="masthead-center">
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
      </div>

      <div className="masthead-side masthead-side-end">
        <CreditStrip credits={RIGHT_CREDITS} />
        <div className="profile-copy">
          <p className="small-label">MELKOV</p>
          <p className="small-subtitle">AI Art Expert Agent</p>
        </div>
        <img className="profile-avatar" src={melkovHead} alt="" aria-hidden="true" />
      </div>
    </header>
  );
}

function CreditStrip({ credits }: { credits: typeof LEFT_CREDITS }) {
  return (
    <ul className="masthead-credits">
      {credits.map((credit) => (
        <li key={credit.name}>
          <img
            className={credit.wordmark ? "credit-logo credit-logo-wide" : "credit-logo"}
            src={credit.src}
            alt={credit.name}
            title={credit.name}
            loading="lazy"
            decoding="async"
          />
        </li>
      ))}
    </ul>
  );
}
