import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { db } from "../lib/db";

function MediaItem({ hash }: { hash: string }) {
  const [url, setUrl] = useState<string | null>(null);
  const [mime, setMime] = useState("");

  useEffect(() => {
    let objectUrl: string | null = null;
    let cancelled = false;

    (async () => {
      const cached = await db.blobs.get(hash);
      const blob = cached ? cached.blob : await fetch(api.mediaUrl(hash)).then((r) => (r.ok ? r.blob() : null));
      if (!blob || cancelled) return;
      objectUrl = URL.createObjectURL(blob);
      setUrl(objectUrl);
      setMime(blob.type);
    })();

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [hash]);

  if (!url) return null;
  if (mime.startsWith("image/")) return <img src={url} alt="" className="card-media" />;
  if (mime.startsWith("audio/")) return <audio src={url} controls className="card-media" />;
  if (mime.startsWith("video/")) return <video src={url} controls className="card-media" />;
  return null;
}

export function MediaRenderer({ hashes }: { hashes: string[] }) {
  if (!hashes.length) return null;
  return (
    <div className="media-list">
      {hashes.map((h) => (
        <MediaItem key={h} hash={h} />
      ))}
    </div>
  );
}
