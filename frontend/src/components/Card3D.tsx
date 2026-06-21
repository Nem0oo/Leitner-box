import { MediaRenderer } from "./MediaRenderer";

interface Card3DProps {
  frontText: string | null;
  frontMedia: string[];
  backText: string | null;
  backMedia: string[];
  flipped: boolean;
  onFlip: () => void;
}

export function Card3D({ frontText, frontMedia, backText, backMedia, flipped, onFlip }: Card3DProps) {
  return (
    <div className="card3d-scene" onClick={onFlip}>
      <div className={`card3d-inner ${flipped ? "flipped" : ""}`}>
        <div className="card3d-face card3d-front">
          {frontText && <p>{frontText}</p>}
          <MediaRenderer hashes={frontMedia} />
        </div>
        <div className="card3d-face card3d-back">
          {backText && <p>{backText}</p>}
          <MediaRenderer hashes={backMedia} />
        </div>
      </div>
    </div>
  );
}
