import feather from "../../assets/feather.svg";

/**
 * A quill writing a line of gold ink, shown while Melkov composes a reply.
 *
 * Shown on every pending turn — answering, reading an attached image,
 * consulting the library, searching a museum. 
 */
export function FeatherWriting() {
  return (
    <div className="feather-writing" aria-hidden="true">
      <svg className="feather-ink" viewBox="0 0 60 16" preserveAspectRatio="none">
        <path
          d="M2 11 C 6 3, 9 3, 10 9 S 14 14, 17 7 S 22 3, 24 10 S 29 13, 32 6 S 37 4, 39 10 S 44 13, 47 7 S 52 5, 58 9"
          pathLength={100}
        />
      </svg>
      <img className="feather-quill" src={feather} alt="" draggable={false} />
    </div>
  );
}
