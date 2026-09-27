import { type ReactNode, useEffect, useId, useRef } from 'react'

import './ConfirmDialog.css'

interface ConfirmDialogProps {
  open: boolean
  title: string
  children: ReactNode
  confirmLabel: string
  busyLabel: string
  /** true enquanto a ação roda: os botões ficam desabilitados. */
  busy?: boolean
  error?: string | null
  onConfirm: () => void
  onCancel: () => void
}

/** Confirmação modal com o <dialog> nativo: foco, modal e Esc já vêm prontos (plan 003, DEC-10). */
function ConfirmDialog({
  open,
  title,
  children,
  confirmLabel,
  busyLabel,
  busy = false,
  error = null,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const titleId = useId()
  const dialogRef = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = dialogRef.current
    if (dialog === null) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  return (
    <dialog
      ref={dialogRef}
      className="confirm-dialog"
      aria-labelledby={titleId}
      onCancel={(event) => {
        // Esc: quem decide fechar é o dono do diálogo (e não durante a ação).
        event.preventDefault()
        if (!busy) onCancel()
      }}
    >
      <h2 id={titleId} className="confirm-dialog__title">
        {title}
      </h2>
      <div className="confirm-dialog__body">{children}</div>
      {error && (
        <p className="confirm-dialog__error" role="alert">
          {error}
        </p>
      )}
      <div className="confirm-dialog__actions">
        <button type="button" className="confirm-dialog__cancel" onClick={onCancel} disabled={busy}>
          Cancelar
        </button>
        <button type="button" className="confirm-dialog__confirm" onClick={onConfirm} disabled={busy}>
          {busy ? busyLabel : confirmLabel}
        </button>
      </div>
    </dialog>
  )
}

export default ConfirmDialog
