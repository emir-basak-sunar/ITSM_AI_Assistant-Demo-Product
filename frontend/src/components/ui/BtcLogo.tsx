const LOGO_SRC = "/btc-logo.png";

export function BtcLogo({
  className = "h-10 w-auto",
  alt = "BTC",
}: {
  className?: string;
  alt?: string;
}) {
  return (
    <img
      src={LOGO_SRC}
      alt={alt}
      className={`object-contain ${className}`}
      draggable={false}
    />
  );
}
