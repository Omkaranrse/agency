'use client';

import * as React from 'react';

const GLYPHS = '01アイウエオカキクケコサシスセソタチツテトナニヌネハヒフヘホマミムメモヤユヨラリルレロワヲン!<>-_\\/[]{}—=+*^?#';

export interface TextScrambleProps {
  text: string;
  className?: string;
  duration?: number;
  speed?: number;
}

export function TextScramble({
  text,
  className,
  duration = 400,
  speed,
}: TextScrambleProps) {
  const [displayText, setDisplayText] = React.useState(text);
  const isFirstRender = React.useRef(true);
  const effectiveDuration = speed ? speed * 15 : duration;

  React.useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }

    let frame = 0;
    const totalFrames = Math.max(10, Math.round((effectiveDuration / 1000) * 60));
    const length = text.length;
    let animationFrameId: number;

    const tick = () => {
      frame++;
      const progress = frame / totalFrames;

      let result = '';
      for (let i = 0; i < length; i++) {
        if (progress >= (i + 1) / length) {
          result += text[i];
        } else {
          result += GLYPHS[Math.floor(Math.random() * GLYPHS.length)];
        }
      }

      setDisplayText(result);

      if (frame < totalFrames) {
        animationFrameId = requestAnimationFrame(tick);
      } else {
        setDisplayText(text);
      }
    };

    animationFrameId = requestAnimationFrame(tick);

    return () => cancelAnimationFrame(animationFrameId);
  }, [text, effectiveDuration]);

  return <span className={className}>{displayText}</span>;
}
