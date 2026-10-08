import { useEffect } from "react";
import type { ReactElement, ReactNode } from "react";
import { createPortal } from "react-dom";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { cn } from "../../lib/utils";

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  className?: string;
}

export function Modal({
  isOpen,
  onClose,
  title,
  children,
  className,
}: ModalProps): ReactElement {
  useEffect(() => {
    if (!isOpen) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    document.addEventListener("keydown", onKey);
    // Stop the page behind the overlay from scrolling while it's open.
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = prevOverflow;
    };
  }, [isOpen, onClose]);

  // Portalled to <body> so the dialog escapes the workspace card's
  // paint/stacking context — rendering it in place made every open
  // repaint the dotted background and the whole config list.
  return createPortal(
    <AnimatePresence>
      {isOpen ? (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            onClick={onClose}
            className="fixed inset-0 z-50 bg-slate-900/50"
          />
          {/* Centering uses a grid wrapper rather than
            `-translate-x-1/2 -translate-y-1/2` on the panel: framer-motion
            writes an inline `transform` for the scale/y animation, which
            overrides the Tailwind translate utilities and left the panel
            hanging from the viewport center point instead of centered on
            it. */}
          <div className="fixed inset-0 z-50 grid place-items-center overflow-y-auto p-4">
            <motion.div
              role="dialog"
              aria-modal="true"
              aria-label={title}
              initial={{ opacity: 0, scale: 0.97 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.97 }}
              transition={{ duration: 0.15, ease: "easeOut" }}
              className={cn(
                "grid w-full max-w-lg gap-4 rounded-xl border border-slate-200 bg-white p-6 shadow-2xl will-change-transform",
                className,
              )}
            >
              <div className="flex flex-col space-y-1.5 sm:text-left">
                <h2 className="flex items-center justify-between text-lg font-semibold leading-none tracking-tight text-slate-900">
                  {title}
                  <button
                    type="button"
                    onClick={onClose}
                    aria-label="Close"
                    className="rounded-sm opacity-70 ring-offset-white transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                  >
                    <X className="h-4 w-4 text-slate-500 hover:text-slate-900" />
                  </button>
                </h2>
              </div>
              {children}
            </motion.div>
          </div>
        </>
      ) : null}
    </AnimatePresence>,
    document.body,
  );
}