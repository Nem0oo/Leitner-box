import { useDirection } from "../lib/direction";

export function DirectionToggle() {
  const [direction, setDirection] = useDirection();
  return (
    <div className="direction-toggle" role="group" aria-label="Direction de révision">
      <button
        className={direction === "recto_to_verso" ? "active" : ""}
        onClick={() => setDirection("recto_to_verso")}
      >
        Normal
      </button>
      <button
        className={direction === "verso_to_recto" ? "active" : ""}
        onClick={() => setDirection("verso_to_recto")}
      >
        Inversé
      </button>
    </div>
  );
}
