import * as Slider from "@radix-ui/react-slider";

// Flat, de-SaaS'd policy slider built on the Radix (shadcn) primitive.
// Snaps to discrete precomputed grid positions; the UI never recomputes risk.
export function StepSlider({ label, options, index, onChange, format }: {
  label: string;
  options: (number | string)[];
  index: number;
  onChange: (i: number) => void;
  format: (v: number | string) => string;
}) {
  return (
    <div>
      <div className="flex items-baseline justify-between">
        <span className="reg text-[10px] text-ink-soft">{label}</span>
        <span className="num text-[13px] font-medium text-ink">{format(options[index])}</span>
      </div>
      <Slider.Root
        className="relative mt-2 flex h-4 w-full touch-none items-center"
        min={0}
        max={options.length - 1}
        step={1}
        value={[index]}
        onValueChange={(v) => onChange(v[0])}
      >
        <Slider.Track className="relative h-[3px] w-full" style={{ background: "#9caf9d" }}>
          <Slider.Range className="absolute h-full" style={{ background: "#285c5e" }} />
        </Slider.Track>
        <Slider.Thumb
          aria-label={label}
          className="block h-3.5 w-3.5 border border-ink focus:outline-none focus-visible:ring-2 focus-visible:ring-accent"
          style={{ background: "#285c5e" }}
        />
      </Slider.Root>
    </div>
  );
}
