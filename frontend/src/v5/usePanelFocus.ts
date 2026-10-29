import { useEffect, useRef, type RefObject } from 'react';

/** V5-only modal focus recovery, including removed or newly disabled controls. */
export function usePanelFocus(open: boolean, confirmation: RefObject<HTMLDialogElement | null>) {
  const panel = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const controls = () => Array.from(panel.current?.querySelectorAll<HTMLElement>('button:not(:disabled),input:not(:disabled),textarea:not(:disabled),select:not(:disabled),summary,a[href],[tabindex="0"]') ?? []).filter(element => element.getClientRects().length > 0);
    const focusEdge = (last = false) => {
      const available = controls();
      (last ? available.at(-1) : available[0])?.focus();
      if (!available.length) panel.current?.focus();
    };
    const repair = () => {
      const active = document.activeElement;
      if (panel.current && !confirmation.current?.open && (!active || !panel.current.contains(active) || active.matches(':disabled'))) focusEdge();
    };
    const onFocus = () => repair();
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== 'Tab' || confirmation.current?.open || !panel.current) return;
      const available = controls(), active = document.activeElement;
      if (!panel.current.contains(active) || active === panel.current || (event.shiftKey ? active === available[0] : active === available.at(-1))) {
        event.preventDefault(); focusEdge(event.shiftKey);
      }
    };
    const onConfirmClose = () => queueMicrotask(repair);
    const observer = new MutationObserver(repair);
    if (panel.current) observer.observe(panel.current, { childList: true, subtree: true, attributes: true, attributeFilter: ['disabled'] });
    const dialog = confirmation.current;
    document.addEventListener('focusin', onFocus);
    document.addEventListener('keydown', onKey, true);
    dialog?.addEventListener('close', onConfirmClose);
    repair();
    return () => { observer.disconnect(); document.removeEventListener('focusin', onFocus); document.removeEventListener('keydown', onKey, true); dialog?.removeEventListener('close', onConfirmClose); };
  }, [open, confirmation]);
  return panel;
}
