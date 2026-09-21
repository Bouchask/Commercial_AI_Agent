import React, { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Check, ShieldCheck, Sparkles, X, Calendar, Table } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { ExcelViewer } from "./ExcelViewer";

const TOOL_NAMES = {
  'db.find_or_create_client': 'Recherche / Création de client',
  'db.create_quote': 'Création de devis',
  'db.create_service': 'Création de service (Catalogue)',
  'db.update_service_price': 'Mise à jour de prix (Catalogue)',
  'document.generate': 'Génération de document (PDF/Excel)',
  'google.calendar.create_event': 'Création d\'événement (Google Agenda)',
  'google.sheets.append_row': 'Mise à jour (Google Sheets)',
  'email.send': 'Envoi d\'email'
};
const getReadableToolName = (tool) => TOOL_NAMES[tool] || tool;

const API_BASE_URL = import.meta.env.VITE_API_URL || "";

function SecureIframe({ url, title }) {
  const [blobUrl, setBlobUrl] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    const fetchBlob = async () => {
      try {
        const token = localStorage.getItem('auth_token');
        const res = await fetch(url, {
          headers: token ? { Authorization: `Bearer ${token}` } : {}
        });
        if (!res.ok) throw new Error("Erreur de chargement");
        const blob = await res.blob();
        if (active) setBlobUrl(URL.createObjectURL(blob));
      } catch (err) {
        if (active) setError(err.message);
      }
    };
    fetchBlob();
    return () => { active = false; };
  }, [url]);

  if (error) return <div className="p-4 text-red-500 text-xs flex items-center justify-center h-full">Erreur: {error}</div>;
  if (!blobUrl) return <div className="p-4 text-md-on-surface-variant text-xs flex items-center justify-center h-full">Chargement du document...</div>;

  return <iframe src={blobUrl} className="w-full h-full border-0" title={title} />;
}

export function ChatMessage({ message, onApprove }) {
  const isUser = message.role === "user";

  /* ── User Bubble (MD3 Secondary Container) ── */
  if (isUser) {
    return (
      <article className="flex justify-end py-3 sm:py-4">
        <div className="max-w-[88%] rounded-3xl bg-md-secondary-container px-5 py-3 text-[15px] leading-6 text-md-on-secondary-container sm:max-w-[78%]">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
        </div>
      </article>
    );
  }

  /* ── Helpers ── */
  const renderValue = (value) => {
    if (Array.isArray(value)) {
      return (
        <div className="flex flex-col gap-1.5 mt-1">
          {value.map((item, i) => (
            <div key={i} className="rounded-xl bg-md-surface-container-low p-2.5 text-xs">
              {typeof item === 'object' && item !== null ? Object.entries(item).map(([k, v]) => (
                <div key={k} className="flex gap-2">
                  <span className="text-md-on-surface-variant">{k}:</span>
                  <span className="text-md-on-surface">{String(v)}</span>
                </div>
              )) : String(item)}
            </div>
          ))}
        </div>
      );
    }
    if (typeof value === 'object' && value !== null) {
      return <span className="text-md-on-surface">{JSON.stringify(value)}</span>;
    }
    return <span className="text-md-on-surface">{String(value)}</span>;
  };

  /* ── Email Preview (MD3 Card) ── */
  const renderEmailPreview = (args) => {
    let attachments = args.attachments;
    if (typeof attachments === 'string') {
      try { attachments = JSON.parse(attachments); } catch(e) { attachments = [attachments]; }
    }
    if (!Array.isArray(attachments)) attachments = [];

    return (
      <div className="mt-4 rounded-3xl bg-md-surface-container overflow-hidden text-[13px] shadow-sm">
        {/* Email Header */}
        <div className="p-4 border-b border-md-outline-variant/20 bg-md-surface-container-high/50">
          <div className="flex gap-4 items-center mb-2">
            <span className="text-md-on-surface-variant font-medium text-xs uppercase tracking-wider w-16 shrink-0">À :</span>
            <span className="text-md-primary font-medium">{args.to}</span>
          </div>
          <div className="flex gap-4 items-center">
            <span className="text-md-on-surface-variant font-medium text-xs uppercase tracking-wider w-16 shrink-0">Objet :</span>
            <span className="text-md-on-surface font-medium">{args.subject}</span>
          </div>
        </div>

        {/* Email Body */}
        <div className="p-4 border-b border-md-outline-variant/20 text-md-on-surface whitespace-pre-wrap leading-relaxed">
          {args.body}
        </div>

        {/* Attachments & Preview */}
        {attachments.length > 0 && (
          <div className="p-4 bg-md-surface-container-high/30">
            <h4 className="text-md-on-surface-variant font-medium text-xs uppercase tracking-wider mb-3">Pièces jointes ({attachments.length})</h4>
            <div className="flex flex-col gap-4">
              {attachments.map((path, idx) => {
                const filename = path.split('/').pop().split('\\').pop();
                const url = `${API_BASE_URL}/api/documents/${filename}`;
                const isPdf = filename.toLowerCase().endsWith('.pdf');
                return (
                  <div key={idx} className="flex flex-col gap-2">
                    <div className="flex items-center gap-2 bg-md-primary-container/50 rounded-full px-3 py-2 text-md-on-primary-container w-fit">
                      <span className="grid place-items-center bg-md-primary text-md-on-primary rounded-full size-6 text-[10px] font-bold">
                        {isPdf ? 'PDF' : 'DOC'}
                      </span>
                      <span className="text-xs truncate max-w-[250px] font-medium">{filename}</span>
                    </div>
                    {/* Preview */}
                    <div className="w-full h-[300px] sm:h-[450px] lg:h-[600px] border border-md-outline-variant/30 rounded-2xl overflow-hidden bg-white mt-1 relative shadow-sm">
                      {isPdf ? (
                        <SecureIframe url={url} title={`Aperçu ${filename}`} />
                      ) : (
                        <ExcelViewer url={url} title={`Aperçu ${filename}`} />
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    );
  };

  /* ── Calendar Preview (MD3 Card) ── */
  const renderCalendarPreview = (args) => {
    return (
      <div className="mt-4 rounded-3xl bg-md-surface-container overflow-hidden text-[13px] shadow-sm">
        <div className="p-4 border-b border-md-outline-variant/20 bg-md-primary-container/30 flex items-center gap-3">
          <Calendar className="size-5 text-md-primary" />
          <span className="text-md-on-primary-container font-medium text-sm">Google Calendar Meeting</span>
        </div>
        <div className="p-4 flex flex-col gap-3">
          <div className="flex gap-4">
            <span className="text-md-on-surface-variant font-medium w-24 shrink-0">Titre :</span>
            <span className="text-md-on-surface font-medium">{args.title}</span>
          </div>
          <div className="flex gap-4">
            <span className="text-md-on-surface-variant font-medium w-24 shrink-0">Date / Heure :</span>
            <span className="text-md-primary">{new Date(args.start_time).toLocaleString('fr-FR')}</span>
          </div>
          {args.attendees && args.attendees.length > 0 && (
            <div className="flex gap-4">
              <span className="text-md-on-surface-variant font-medium w-24 shrink-0">Invités :</span>
              <span className="text-md-on-surface">{args.attendees.join(', ')}</span>
            </div>
          )}
          {args.description && (
            <div className="flex gap-4">
              <span className="text-md-on-surface-variant font-medium w-24 shrink-0">Description :</span>
              <span className="text-md-on-surface-variant text-xs">{args.description}</span>
            </div>
          )}
        </div>
      </div>
    );
  };

  /* ── Sheets Preview (MD3 Card) ── */
  const renderSheetsPreview = (args) => {
    return (
      <div className="mt-4 rounded-3xl bg-md-surface-container overflow-hidden text-[13px] shadow-sm">
        <div className="p-4 border-b border-md-outline-variant/20 bg-md-tertiary-container/30 flex items-center gap-3">
          <Table className="size-5 text-md-tertiary" />
          <span className="text-md-on-tertiary-container font-medium text-sm">Google Sheets Export</span>
        </div>
        <div className="p-4 flex flex-col gap-3">
          <div className="flex gap-4">
            <span className="text-md-on-surface-variant font-medium w-24 shrink-0">ID Fichier :</span>
            <span className="text-md-on-surface font-mono text-xs">{args.spreadsheet_id || "Automatique (Nouveau ou Existant)"}</span>
          </div>
          <div className="flex gap-4">
            <span className="text-md-on-surface-variant font-medium w-24 shrink-0">Données :</span>
            <div className="flex gap-2 flex-wrap">
              {args.values?.map((val, i) => (
                <span key={i} className="bg-md-secondary-container px-2.5 py-1 rounded-full text-md-on-secondary-container text-xs font-medium">
                  {String(val)}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  };

  /* ── Agent Message ── */
  return (
    <article className="flex gap-3 py-4 sm:gap-4 sm:py-5">
      <div className="mt-0.5 grid size-7 shrink-0 place-items-center rounded-full bg-md-primary text-white shadow-sm">
        <Sparkles className="size-3.5" />
      </div>
      <div className="min-w-0 flex-1 pt-0.5">
        <div className="agent-markdown text-[15px] leading-7 text-md-on-surface">
          <ReactMarkdown 
            remarkPlugins={[remarkGfm]}
            components={{
              a: ({node, ...props}) => {
                const isCalendar = props.href?.includes('calendar.google.com');
                const isSheets = props.href?.includes('docs.google.com/spreadsheets');
                
                return (
                  <a href={props.href} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 rounded-full bg-md-primary-container px-3.5 py-1.5 text-[13px] font-medium text-md-on-primary-container hover:bg-md-primary hover:text-md-on-primary transition-all duration-300 ease-[cubic-bezier(0.2,0,0,1)] my-2 shadow-sm active:scale-95">
                    {isCalendar && <Calendar className="size-3.5" />}
                    {isSheets && <Table className="size-3.5" />}
                    {isCalendar ? "Ouvrir dans Google Agenda" : isSheets ? "Ouvrir dans Google Sheets" : "Ouvrir le lien"}
                  </a>
                );
              }
            }}
          >
            {message.content}
          </ReactMarkdown>
        </div>

        {/* ── Approval Card (MD3 Surface + Tertiary accent) ── */}
        {message.approval && (
          <section className="mt-4 rounded-3xl bg-md-surface-container border border-md-tertiary/20 p-5 shadow-sm">
            <div className="flex items-start gap-3">
              <span className="grid size-8 shrink-0 place-items-center rounded-full bg-md-tertiary-container text-md-tertiary"><ShieldCheck className="size-4" /></span>
              <div>
                <h2 className="text-sm font-medium text-md-on-surface">Validation requise</h2>
                <p className="mt-0.5 text-xs leading-5 text-md-on-surface-variant">
                  L'agent souhaite exécuter l'action suivante : <span className="font-medium text-md-primary bg-md-primary-container/30 px-2 py-0.5 rounded-full">{getReadableToolName(message.approval.tool)}</span>
                </p>
              </div>
            </div>
            
            {/* ── Invoice / Quote Preview ── */}
            {['db.create_quote', 'document.generate'].includes(message.approval.tool) && message.approval.arguments ? (
              <div className="mt-4 rounded-3xl bg-md-surface-container-high/50 overflow-hidden text-[13px] shadow-sm border border-md-outline-variant/20">
                {/* Header */}
                <div className="flex justify-between items-end p-5 border-b border-md-outline-variant/20">
                  <div>
                    <h3 className="text-lg font-medium text-md-on-surface uppercase tracking-widest">
                      {message.approval.arguments.document_type === 'invoice' ? 'Facture' : 'Devis'}
                    </h3>
                    <p className="text-md-on-surface-variant mt-1">{message.approval.arguments.client_name || `Client #${message.approval.arguments.client_id || 'N/A'}`}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-md-on-surface-variant text-xs uppercase tracking-wider mb-0.5">Montant TTC</p>
                    <p className="text-xl font-medium text-md-primary">{(message.approval.arguments.total_ttc || 0).toFixed(2)} MAD</p>
                  </div>
                </div>

                {/* Items Table */}
                <div className="p-0">
                  <div className="grid grid-cols-12 gap-2 px-5 py-2.5 border-b border-md-outline-variant/20 bg-md-surface-container-high/40 text-md-on-surface-variant text-[10px] font-medium uppercase tracking-wider">
                    <div className="col-span-6">Description</div>
                    <div className="col-span-2 text-right">Qté</div>
                    <div className="col-span-2 text-right">Prix U.</div>
                    <div className="col-span-2 text-right">Total</div>
                  </div>
                  <div className="flex flex-col">
                    {message.approval.arguments.items?.map((item, idx) => (
                      <div key={idx} className="grid grid-cols-12 gap-2 px-5 py-3.5 border-b border-md-outline-variant/10 last:border-0 text-md-on-surface">
                        <div className="col-span-6">
                          <div className="font-medium">{item.code}</div>
                          {item.description && <div className="text-md-on-surface-variant text-xs truncate mt-0.5">{item.description}</div>}
                        </div>
                        <div className="col-span-2 text-right">{item.quantity}</div>
                        <div className="col-span-2 text-right">{(item.price || item.unit_price || 0).toFixed(2)} MAD</div>
                        <div className="col-span-2 text-right font-medium">{(item.line_total || (item.quantity * (item.price || item.unit_price || 0))).toFixed(2)} MAD</div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Totals */}
                <div className="bg-md-surface-container-low/50 p-5 flex justify-end">
                  <div className="w-48 flex flex-col gap-1.5 text-xs">
                    <div className="flex justify-between text-md-on-surface-variant">
                      <span>Total HT</span>
                      <span>{(message.approval.arguments.total_ht || message.approval.arguments.original_subtotal || 0).toFixed(2)} MAD</span>
                    </div>
                    {message.approval.arguments.discount_amount > 0 && (
                      <div className="flex justify-between text-md-tertiary">
                        <span>Remise</span>
                        <span>-{(message.approval.arguments.discount_amount || 0).toFixed(2)} MAD</span>
                      </div>
                    )}
                    <div className="flex justify-between text-md-on-surface-variant">
                      <span>TVA</span>
                      <span>{(message.approval.arguments.tax || message.approval.arguments.total_tax || 0).toFixed(2)} MAD</span>
                    </div>
                    <div className="flex justify-between text-md-primary font-medium pt-1.5 border-t border-md-outline-variant/30 mt-1 text-[13px]">
                      <span>Total TTC</span>
                      <span>{(message.approval.arguments.total_ttc || 0).toFixed(2)} MAD</span>
                    </div>
                  </div>
                </div>
              </div>
            ) : message.approval.tool === 'email.send' && message.approval.arguments ? (
              renderEmailPreview(message.approval.arguments)
            ) : message.approval.tool === 'google.calendar.create_meeting' && message.approval.arguments ? (
              renderCalendarPreview(message.approval.arguments)
            ) : message.approval.tool === 'google.sheets.append_row' && message.approval.arguments ? (
              renderSheetsPreview(message.approval.arguments)
            ) : (
              <div className="mt-4 rounded-2xl bg-md-surface-container-high/50 border border-md-outline-variant/20 overflow-hidden">
                <div className="px-4 py-2.5 border-b border-md-outline-variant/20 bg-md-surface-container-high/40 text-[10px] font-medium text-md-on-surface-variant uppercase tracking-wider flex justify-between items-center">
                  <span>Données de la requête</span>
                </div>
                <div className="p-4 grid gap-1 text-[13px]">
                  {message.approval.arguments && Object.entries(message.approval.arguments).map(([key, value]) => (
                    <div key={key} className="flex flex-col sm:flex-row sm:items-start gap-1 py-1.5 border-b border-md-outline-variant/10 last:border-0">
                      <div className="text-md-on-surface-variant font-medium sm:w-1/3 shrink-0">{key}</div>
                      <div className="text-md-on-surface break-words flex-1">{renderValue(value)}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ── Action Buttons or Status Badge (MD3 Pill) ── */}
            <div className="mt-5 flex flex-wrap gap-2">
              {!message.approval.status || message.approval.status === "pending" ? (
                <>
                  <button onClick={() => onApprove(message.approval, true)} className="inline-flex items-center gap-1.5 rounded-full bg-md-primary px-5 py-2 text-[13px] font-medium text-md-on-primary shadow-sm hover:bg-md-primary/90 hover:shadow-md transition-all duration-300 ease-[cubic-bezier(0.2,0,0,1)] active:scale-95">
                    <Check className="size-3.5" /> Approuver
                  </button>
                  <button onClick={() => onApprove(message.approval, false)} className="inline-flex items-center gap-1.5 rounded-full border border-md-outline bg-transparent px-5 py-2 text-[13px] font-medium text-md-on-surface hover:bg-md-primary/5 transition-all duration-300 ease-[cubic-bezier(0.2,0,0,1)] active:scale-95">
                    <X className="size-3.5" /> Refuser
                  </button>
                </>
              ) : message.approval.status === "approved" ? (
                <div className="inline-flex items-center gap-1.5 rounded-full bg-green-100/50 border border-green-500/30 px-5 py-2 text-[13px] font-medium text-green-700 shadow-sm">
                  <Check className="size-3.5" /> Action approuvée
                </div>
              ) : (
                <div className="inline-flex items-center gap-1.5 rounded-full bg-red-100/50 border border-red-500/30 px-5 py-2 text-[13px] font-medium text-red-700 shadow-sm">
                  <X className="size-3.5" /> Action refusée
                </div>
              )}
            </div>
          </section>
        )}
      </div>
    </article>
  );
}
