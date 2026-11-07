import type { ReactNode } from "react";

interface IconProps {
  size?: number;
}

interface SvgProps extends IconProps {
  strokeWidth?: number;
  children: ReactNode;
}

/** Stroke icons drawn on a 24px grid. Decorative: the label next to them says what they mean. */
function Svg({ size = 20, strokeWidth = 1.8, children }: SvgProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      style={{ flex: "0 0 auto" }}
    >
      {children}
    </svg>
  );
}

export const LibraryIcon = (props: IconProps) => (
  <Svg {...props}>
    <rect x="3" y="3" width="7" height="7" rx="1" />
    <rect x="14" y="3" width="7" height="7" rx="1" />
    <rect x="3" y="14" width="7" height="7" rx="1" />
    <rect x="14" y="14" width="7" height="7" rx="1" />
  </Svg>
);

export const DownloadIcon = (props: IconProps) => (
  <Svg {...props}>
    <path d="M12 3v12" />
    <path d="m7 10 5 5 5-5" />
    <path d="M4 21h16" />
  </Svg>
);

export const GlobeIcon = (props: IconProps) => (
  <Svg {...props}>
    <circle cx="12" cy="12" r="9" />
    <path d="M3 12h18" />
    <path d="M12 3c3 3.2 3 14.8 0 18M12 3c-3 3.2-3 14.8 0 18" />
  </Svg>
);

export const SlidersIcon = (props: IconProps) => (
  <Svg {...props}>
    <path d="M4 7h10M18 7h2M4 17h2M10 17h10" />
    <circle cx="16" cy="7" r="2" />
    <circle cx="8" cy="17" r="2" />
  </Svg>
);

export const ChevronLeftIcon = ({ size = 16 }: IconProps) => (
  <Svg size={size} strokeWidth={2}>
    <path d="m15 18-6-6 6-6" />
  </Svg>
);

export const PauseIcon = ({ size = 18 }: IconProps) => (
  <Svg size={size} strokeWidth={2}>
    <path d="M8 5v14M16 5v14" />
  </Svg>
);

export const CloseIcon = ({ size = 18 }: IconProps) => (
  <Svg size={size} strokeWidth={2}>
    <path d="M6 6l12 12M18 6 6 18" />
  </Svg>
);

export const CheckCircleIcon = (props: IconProps) => (
  <Svg {...props} strokeWidth={2}>
    <circle cx="12" cy="12" r="9" />
    <path d="m8 12 3 3 5-6" />
  </Svg>
);

export const MinusCircleIcon = (props: IconProps) => (
  <Svg {...props} strokeWidth={2}>
    <circle cx="12" cy="12" r="9" />
    <path d="M8 12h8" />
  </Svg>
);
