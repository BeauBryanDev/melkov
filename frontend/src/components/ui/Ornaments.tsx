import React from "react";

/**
 * 4 Ornate Gold Corner Brackets for Panels
 */
export function PanelCorners() {
  return (
    <div className="panel-corners-layer" aria-hidden="true">
      {/* Top Left */}
      <svg className="panel-corner corner-tl" width="28" height="28" viewBox="0 0 28 28" fill="none">
        <path d="M2 26V6C2 3.79086 3.79086 2 6 2H26" stroke="url(#gold-grad)" strokeWidth="1.5" />
        <path d="M6 6H16M6 6V16" stroke="url(#gold-grad)" strokeWidth="1" opacity="0.6" />
        <circle cx="4" cy="4" r="2" fill="#ffd87d" />
        <path d="M2 10L10 2" stroke="url(#gold-grad)" strokeWidth="1" opacity="0.8" />
        <defs>
          <linearGradient id="gold-grad" x1="0" y1="0" x2="28" y2="28" gradientUnits="userSpaceOnUse">
            <stop stopColor="#ffe49e" />
            <stop offset="0.5" stopColor="#e0b15b" />
            <stop offset="1" stopColor="#8d6420" />
          </linearGradient>
        </defs>
      </svg>

      {/* Top Right */}
      <svg className="panel-corner corner-tr" width="28" height="28" viewBox="0 0 28 28" fill="none">
        <path d="M26 26V6C26 3.79086 24.2091 2 22 2H2" stroke="url(#gold-grad)" strokeWidth="1.5" />
        <path d="M22 6H12M22 6V16" stroke="url(#gold-grad)" strokeWidth="1" opacity="0.6" />
        <circle cx="24" cy="4" r="2" fill="#ffd87d" />
        <path d="M26 10L18 2" stroke="url(#gold-grad)" strokeWidth="1" opacity="0.8" />
      </svg>

      {/* Bottom Left */}
      <svg className="panel-corner corner-bl" width="28" height="28" viewBox="0 0 28 28" fill="none">
        <path d="M2 2V22C2 24.2091 3.79086 26 6 26H26" stroke="url(#gold-grad)" strokeWidth="1.5" />
        <path d="M6 22H16M6 22V12" stroke="url(#gold-grad)" strokeWidth="1" opacity="0.6" />
        <circle cx="4" cy="24" r="2" fill="#ffd87d" />
        <path d="M2 18L10 26" stroke="url(#gold-grad)" strokeWidth="1" opacity="0.8" />
      </svg>

      {/* Bottom Right */}
      <svg className="panel-corner corner-br" width="28" height="28" viewBox="0 0 28 28" fill="none">
        <path d="M26 2V22C26 24.2091 24.2091 26 22 26H2" stroke="url(#gold-grad)" strokeWidth="1.5" />
        <path d="M22 22H12M22 22V12" stroke="url(#gold-grad)" strokeWidth="1" opacity="0.6" />
        <circle cx="24" cy="24" r="2" fill="#ffd87d" />
        <path d="M26 18L18 26" stroke="url(#gold-grad)" strokeWidth="1" opacity="0.8" />
      </svg>
    </div>
  );
}

/**
 * Heavy 3D Gilded Frame Corners for picture frame
 */
export function GildedFrameCorners() {
  return (
    <div className="gilded-corners-layer" aria-hidden="true">
      {/* TL */}
      <svg className="gilded-corner corner-tl" width="48" height="48" viewBox="0 0 48 48" fill="none">
        <path d="M4 44V12C4 7.58172 7.58172 4 12 4H44" stroke="url(#frame-gold)" strokeWidth="4" strokeLinecap="round" />
        <path d="M10 44V16C10 12.6863 12.6863 10 16 10H44" stroke="#ffd87d" strokeWidth="1.5" />
        <path d="M4 4C14 4 4 14 18 18C14 4 4 14 4 4Z" fill="url(#frame-gold)" />
        <circle cx="12" cy="12" r="3" fill="#ffe7a3" />
        <defs>
          <linearGradient id="frame-gold" x1="0" y1="0" x2="48" y2="48" gradientUnits="userSpaceOnUse">
            <stop stopColor="#fff1c5" />
            <stop offset="0.4" stopColor="#e0b15b" />
            <stop offset="0.8" stopColor="#a3762b" />
            <stop offset="1" stopColor="#5c3f10" />
          </linearGradient>
        </defs>
      </svg>

      {/* TR */}
      <svg className="gilded-corner corner-tr" width="48" height="48" viewBox="0 0 48 48" fill="none">
        <path d="M44 44V12C44 7.58172 40.4183 4 36 4H4" stroke="url(#frame-gold)" strokeWidth="4" strokeLinecap="round" />
        <path d="M38 44V16C38 12.6863 35.3137 10 32 10H4" stroke="#ffd87d" strokeWidth="1.5" />
        <path d="M44 4C34 4 44 14 30 18C34 4 44 14 44 4Z" fill="url(#frame-gold)" />
        <circle cx="36" cy="12" r="3" fill="#ffe7a3" />
      </svg>

      {/* BL */}
      <svg className="gilded-corner corner-bl" width="48" height="48" viewBox="0 0 48 48" fill="none">
        <path d="M4 4V36C4 40.4183 7.58172 44 12 44H44" stroke="url(#frame-gold)" strokeWidth="4" strokeLinecap="round" />
        <path d="M10 4V32C10 35.3137 12.6863 38 16 38H44" stroke="#ffd87d" strokeWidth="1.5" />
        <path d="M4 44C14 44 4 34 18 30C14 44 4 34 4 44Z" fill="url(#frame-gold)" />
        <circle cx="12" cy="36" r="3" fill="#ffe7a3" />
      </svg>

      {/* BR */}
      <svg className="gilded-corner corner-br" width="48" height="48" viewBox="0 0 48 48" fill="none">
        <path d="M44 4V36C44 40.4183 40.4183 44 36 44H4" stroke="url(#frame-gold)" strokeWidth="4" strokeLinecap="round" />
        <path d="M38 4V32C38 35.3137 35.3137 38 32 38H4" stroke="#ffd87d" strokeWidth="1.5" />
        <path d="M44 44C34 44 44 34 30 30C34 44 44 34 44 44Z" fill="url(#frame-gold)" />
        <circle cx="36" cy="36" r="3" fill="#ffe7a3" />
      </svg>
    </div>
  );
}

/**
 * Gold Header Diamond / Wing Flourish
 */
export function GoldHeaderFlourish({ className = "" }: { className?: string }) {
  return (
    <svg className={`gold-flourish ${className}`} width="36" height="16" viewBox="0 0 36 16" fill="none" aria-hidden="true">
      <path d="M0 8H12L18 2L24 8H36" stroke="url(#flourish-gold)" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M18 2L14 8L18 14L22 8L18 2Z" fill="url(#flourish-gold)" />
      <circle cx="18" cy="8" r="2" fill="#fff" />
      <defs>
        <linearGradient id="flourish-gold" x1="0" y1="0" x2="36" y2="16" gradientUnits="userSpaceOnUse">
          <stop stopColor="#ffe49e" />
          <stop offset="0.5" stopColor="#e0b15b" />
          <stop offset="1" stopColor="#8d6420" />
        </linearGradient>
      </defs>
    </svg>
  );
}

/**
 * Royal Crest Emblem (Crown + Wreath + Diamond)
 */
export function HouseOfValtoriaCrest({ className = "" }: { className?: string }) {
  return (
    <svg className={`crest-svg ${className}`} width="44" height="44" viewBox="0 0 44 44" fill="none" aria-hidden="true">
      {/* Outer Wreath / Circle */}
      <circle cx="22" cy="22" r="20" stroke="url(#crest-gold)" strokeWidth="1.5" strokeDasharray="3 2" />
      <circle cx="22" cy="22" r="17" stroke="url(#crest-gold)" strokeWidth="0.75" opacity="0.6" />
      {/* Crown */}
      <path d="M12 28L10 16L17 21L22 13L27 21L34 16L32 28H12Z" fill="url(#crest-gold)" stroke="#ffd87d" strokeWidth="0.5" />
      <circle cx="10" cy="15" r="1.5" fill="#fff" />
      <circle cx="22" cy="12" r="1.5" fill="#fff" />
      <circle cx="34" cy="15" r="1.5" fill="#fff" />
      {/* Crown Base */}
      <rect x="12" y="27" width="20" height="3" rx="1" fill="#ffd87d" />
      <circle cx="16" cy="28.5" r="0.75" fill="#5c3f10" />
      <circle cx="22" cy="28.5" r="0.75" fill="#5c3f10" />
      <circle cx="28" cy="28.5" r="0.75" fill="#5c3f10" />
      <defs>
        <linearGradient id="crest-gold" x1="0" y1="0" x2="44" y2="44" gradientUnits="userSpaceOnUse">
          <stop stopColor="#fff1c5" />
          <stop offset="0.5" stopColor="#e0b15b" />
          <stop offset="1" stopColor="#8d6420" />
        </linearGradient>
      </defs>
    </svg>
  );
}

/**
 * Melkov Portrait Avatar Component
 */
export function MelkovPortraitAvatar({ size = 48, className = "" }: { size?: number; className?: string }) {
  return (
    <div className={`melkov-avatar-wrapper ${className}`} style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox="0 0 64 64" fill="none" aria-hidden="true">
        <defs>
          <radialGradient id="portrait-bg" cx="50%" cy="30%" r="70%">
            <stop offset="0%" stopColor="#1e3a6a" />
            <stop offset="70%" stopColor="#0a162b" />
            <stop offset="100%" stopColor="#030814" />
          </radialGradient>
          <linearGradient id="avatar-ring" x1="0" y1="0" x2="64" y2="64">
            <stop stopColor="#ffe7a3" />
            <stop offset="0.5" stopColor="#e0b15b" />
            <stop offset="1" stopColor="#7a5518" />
          </linearGradient>
        </defs>

        {/* Outer Ring */}
        <circle cx="32" cy="32" r="31" fill="url(#portrait-bg)" stroke="url(#avatar-ring)" strokeWidth="2" />
        <circle cx="32" cy="32" r="28" stroke="#ffe7a3" strokeWidth="0.5" opacity="0.6" />

        {/* Prince Silhouette & Jacket */}
        {/* Hair */}
        <path d="M22 22C20 18 24 12 32 12C40 12 44 18 42 22C44 20 45 24 43 27C41 30 40 26 38 26C35 26 35 28 32 28C29 28 29 26 26 26C24 26 23 30 21 27C19 24 20 20 22 22Z" fill="#d9a24a" />
        {/* Face */}
        <path d="M24 24C24 24 26 34 32 34C38 34 40 24 40 24C40 30 37 38 32 38C27 38 24 30 24 24Z" fill="#f5ce9f" />
        {/* Eyes & Eyebrows */}
        <path d="M26 25Q28 24 30 25" stroke="#7a5223" strokeWidth="1" strokeLinecap="round" />
        <path d="M34 25Q36 24 38 25" stroke="#7a5223" strokeWidth="1" strokeLinecap="round" />
        {/* Nose & Mouth */}
        <path d="M32 27V30L33 30.5" stroke="#d49b65" strokeWidth="0.8" strokeLinecap="round" fill="none" />
        <path d="M30 33Q32 34.5 34 33" stroke="#b86d53" strokeWidth="1" strokeLinecap="round" fill="none" />

        {/* Royal Blue Jacket & Gold Collar */}
        <path d="M12 56C12 44 20 38 32 38C44 38 52 44 52 56H12Z" fill="#0d2448" stroke="url(#avatar-ring)" strokeWidth="1" />
        {/* High Gold Embroidered Collar */}
        <path d="M24 38L32 46L40 38" fill="#142e58" stroke="url(#avatar-ring)" strokeWidth="1.5" />
        <path d="M28 38L32 42L36 38" fill="url(#avatar-ring)" />
        {/* Medallion / Star */}
        <circle cx="32" cy="48" r="2.5" fill="#ffe7a3" />
        <path d="M32 44V52M28 48H36" stroke="#e0b15b" strokeWidth="0.75" />
      </svg>
    </div>
  );
}

/**
 * Illuminated Gothic/Baroque Drop Cap Box
 */
export function IlluminatedLetter({ letter = "I" }: { letter?: string }) {
  return (
    <div className="illuminated-box" aria-hidden="true">
      <svg className="illuminated-frame" width="76" height="96" viewBox="0 0 76 96" fill="none">
        <defs>
          <linearGradient id="illum-gold" x1="0" y1="0" x2="76" y2="96">
            <stop stopColor="#ffe49e" />
            <stop offset="0.5" stopColor="#e0b15b" />
            <stop offset="1" stopColor="#6e4c16" />
          </linearGradient>
          <radialGradient id="illum-bg" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#1a325c" />
            <stop offset="100%" stopColor="#081020" />
          </radialGradient>
        </defs>

        {/* Outer Gilded Box */}
        <rect x="3" y="3" width="70" height="90" rx="6" fill="url(#illum-bg)" stroke="url(#illum-gold)" strokeWidth="2" />
        <rect x="7" y="7" width="62" height="82" rx="4" stroke="#ffe49e" strokeWidth="0.75" strokeDasharray="4 2" opacity="0.7" />

        {/* Arch / Gothic Window Silhouette */}
        <path d="M20 75V40C20 28 38 20 38 20C38 20 56 28 56 40V75H20Z" fill="#0b172d" stroke="url(#illum-gold)" strokeWidth="0.75" opacity="0.6" />

        {/* Castle Spire / Arch Ornaments */}
        <path d="M38 20V75M28 45H48" stroke="url(#illum-gold)" strokeWidth="0.5" opacity="0.4" />

        {/* Corner Leaf Filigree */}
        <circle cx="12" cy="12" r="2" fill="#ffe49e" />
        <circle cx="64" cy="12" r="2" fill="#ffe49e" />
        <circle cx="12" cy="84" r="2" fill="#ffe49e" />
        <circle cx="64" cy="84" r="2" fill="#ffe49e" />
      </svg>
      <span className="illuminated-text">{letter}</span>
    </div>
  );
}
