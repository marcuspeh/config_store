import { useEffect, useId, useMemo, useRef, useState } from "react";
import { Check, ChevronDown, Loader2, X as XIcon } from "lucide-react";
import clsx from "clsx";

// ProjectCombobox is a text input + popover dropdown. The user can
// type any project name (including ones not in `options`); the popover
// shows the matching options from the list, and Enter / click commits.
//
// Mirrors the look-and-feel of the logging_system frontend so the two
// admin UIs feel consistent.
interface ProjectComboboxProps {
  value: string;
  onChange: (next: string) => void;
  options: string[];
  isLoading?: boolean;
  id?: string;
  placeholder?: string;
  className?: string;
  onBlur?: () => void;
}

export function ProjectCombobox({
  value,
  onChange,
  options,
  isLoading,
  id,
  placeholder,
  className,
  onBlur,
}: ProjectComboboxProps) {
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState<number>(-1);
  const listboxId = useId();
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const trimmed = value.trim();
  const matched = useMemo(() => {
    const q = trimmed.toLowerCase();
    if (q === "") return options;
    return options.filter((o) => o.toLowerCase().includes(q));
  }, [options, trimmed]);

  const showCustomHint = trimmed !== "" && !options.includes(trimmed);
  const totalRows = matched.length + (showCustomHint ? 1 : 0);

  useEffect(() => {
    setActiveIndex(matched.length > 0 ? 0 : -1);
  }, [matched.length, trimmed]);

  useEffect(() => {
    if (!open) return;
    const onDocClick = (e: MouseEvent) => {
      if (!containerRef.current?.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [open]);

  const commit = (next: string) => {
    onChange(next);
    setOpen(false);
    inputRef.current?.focus();
  };

  const clear = () => {
    onChange("");
    inputRef.current?.focus();
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (!open) setOpen(true);
      if (totalRows > 0) setActiveIndex((i) => (i + 1) % totalRows);
      return;
    }
    if (e.key === "ArrowUp") {
      e.preventDefault();
      if (!open) setOpen(true);
      if (totalRows > 0) setActiveIndex((i) => (i <= 0 ? totalRows - 1 : i - 1));
      return;
    }
    if (e.key === "Home") {
      if (open && totalRows > 0) {
        e.preventDefault();
        setActiveIndex(0);
      }
      return;
    }
    if (e.key === "End") {
      if (open && totalRows > 0) {
        e.preventDefault();
        setActiveIndex(totalRows - 1);
      }
      return;
    }
    if (e.key === "Enter") {
      if (open && activeIndex >= 0) {
        e.preventDefault();
        if (activeIndex < matched.length) {
          commit(matched[activeIndex]);
        } else if (showCustomHint) {
          commit(trimmed);
        }
      }
      return;
    }
    if (e.key === "Escape") {
      if (open) {
        e.preventDefault();
        setOpen(false);
      }
      return;
    }
  };

  return (
    <div ref={containerRef} className={clsx("relative", className)}>
      <div
        role="combobox"
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-owns={listboxId}
        className="relative"
      >
        <input
          ref={inputRef}
          id={id}
          type="text"
          autoComplete="off"
          spellCheck={false}
          placeholder={placeholder ?? "Type or pick a project"}
          value={value}
          onChange={(e) => {
            onChange(e.target.value);
            setOpen(true);
          }}
          onFocus={() => setOpen(true)}
          onBlur={onBlur}
          onKeyDown={onKeyDown}
          aria-autocomplete="list"
          aria-controls={listboxId}
          aria-activedescendant={
            open && activeIndex >= 0 ? `${listboxId}-opt-${activeIndex}` : undefined
          }
          className="w-full rounded-md border border-slate-200 bg-white px-3 py-1.5 pr-16 font-mono text-sm focus:border-slate-400 focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 placeholder:font-sans placeholder:text-slate-400"
        />
        <div className="pointer-events-none absolute inset-y-0 right-2 flex items-center gap-1 text-slate-400">
          {isLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : null}
          {value ? (
            <button
              type="button"
              tabIndex={-1}
              onClick={clear}
              className="pointer-events-auto rounded p-0.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
              aria-label="Clear project"
            >
              <XIcon className="h-3.5 w-3.5" />
            </button>
          ) : null}
          <ChevronDown
            className={clsx(
              "h-3.5 w-3.5 transition-transform",
              open ? "rotate-180 text-slate-600" : "",
            )}
          />
        </div>
      </div>

      {open ? (
        <ul
          id={listboxId}
          role="listbox"
          className="absolute z-20 mt-1 max-h-60 w-full overflow-auto rounded-md border border-slate-200 bg-white py-1 font-sans text-sm shadow-lg"
        >
          {matched.length === 0 && !showCustomHint ? (
            <li className="px-3 py-2 text-xs text-slate-500">
              {isLoading ? "Loading projects…" : "No projects match."}
            </li>
          ) : null}

          {matched.map((option, i) => {
            const selected = option === value;
            const active = i === activeIndex;
            return (
              <li
                key={option}
                id={`${listboxId}-opt-${i}`}
                role="option"
                aria-selected={selected}
                onMouseEnter={() => setActiveIndex(i)}
                onMouseDown={(e) => {
                  e.preventDefault();
                  commit(option);
                }}
                className={clsx(
                  "flex cursor-pointer items-center gap-2 px-3 py-1.5",
                  active ? "bg-slate-100 text-slate-900" : "text-slate-700",
                )}
              >
                <span className="flex-1 truncate font-mono">{option}</span>
                {selected ? <Check className="h-3.5 w-3.5 text-slate-500" /> : null}
              </li>
            );
          })}

          {showCustomHint ? (
            <li
              id={`${listboxId}-opt-${matched.length}`}
              role="option"
              aria-selected={false}
              onMouseEnter={() => setActiveIndex(matched.length)}
              onMouseDown={(e) => {
                e.preventDefault();
                commit(trimmed);
              }}
              className={clsx(
                "flex cursor-pointer items-center gap-2 border-t border-slate-100 px-3 py-1.5 text-slate-700",
                activeIndex === matched.length ? "bg-slate-100" : "",
              )}
            >
              <span className="flex-1 truncate">
                Use{" "}
                <span className="rounded bg-slate-100 px-1.5 py-0.5 font-mono text-xs text-slate-900">
                  {trimmed}
                </span>{" "}
                as a custom project
              </span>
            </li>
          ) : null}
        </ul>
      ) : null}
    </div>
  );
}
