import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { C, INTER, MONO, ramp } from "../theme";
import { at, type SceneProps } from "../timing";

// Lucide icons (ISC), the same set the app inlines.
const ICONS: Record<string, React.ReactNode> = {
  shield: (
    <>
      <path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z" />
      <path d="m9 12 2 2 4-4" />
    </>
  ),
  tag: (
    <>
      <path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.704 8.704a2.426 2.426 0 0 0 3.42 0l6.58-6.58a2.426 2.426 0 0 0 0-3.42z" />
      <circle cx="7.5" cy="7.5" r=".5" fill="currentColor" />
    </>
  ),
  check: (
    <>
      <circle cx="12" cy="12" r="10" />
      <path d="m9 12 2 2 4-4" />
    </>
  ),
  flag: (
    <>
      <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
      <line x1="4" x2="4" y1="22" y2="15" />
    </>
  ),
};

const CARDS: { icon: string; text: React.ReactNode }[] = [
  {
    icon: "shield",
    text: (
      <>
        <span style={{ fontFamily: MONO, fontWeight: 500 }}>
          delivered_amount
        </span>
        : partial payments can't inflate the amounts
      </>
    ),
  },
  {
    icon: "tag",
    text: "Destination tag: it points to one customer's account at the exchange",
  },
  { icon: "check", text: "7 of 7 traced transfers match the ledger" },
  { icon: "flag", text: "Public flags, signed with the analyst's name" },
];

/** Scene 8: four cards in a 2x2 grid, one per bar. */
export const WhyXrpl: React.FC<SceneProps> = (p) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill
      style={{
        alignItems: "center",
        justifyContent: "center",
        fontFamily: INTER,
      }}
    >
      <div
        style={{
          color: C.blue,
          fontSize: 22,
          fontWeight: 600,
          letterSpacing: "0.16em",
          marginBottom: 34,
          opacity: ramp(frame, 0, 24),
        }}
      >
        WHY XRPL
      </div>
      <div
        style={{ display: "grid", gridTemplateColumns: "760px 760px", gap: 36 }}
      >
        {CARDS.map((card, i) => {
          const e = ramp(frame, at(p, `card${i + 1}`), 30);
          return (
            <div
              key={card.icon}
              style={{
                height: 190,
                padding: "0 40px",
                borderRadius: 26,
                display: "flex",
                alignItems: "center",
                gap: 30,
                background: "rgba(225, 232, 239, 0.05)",
                border: "1px solid rgba(225, 232, 239, 0.12)",
                opacity: e,
                transform: `translateY(${(1 - e) * 12}px) scale(${0.98 + 0.02 * e})`,
              }}
            >
              <div
                style={{
                  flex: "0 0 88px",
                  height: 88,
                  borderRadius: 22,
                  display: "grid",
                  placeItems: "center",
                  background: "rgba(94, 162, 245, 0.12)",
                  color: C.blue,
                }}
              >
                <svg
                  width={50}
                  height={50}
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth={1.6}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  {ICONS[card.icon]}
                </svg>
              </div>
              <div
                style={{
                  color: C.white,
                  fontSize: 34,
                  fontWeight: 600,
                  lineHeight: 1.25,
                }}
              >
                {card.text}
              </div>
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
