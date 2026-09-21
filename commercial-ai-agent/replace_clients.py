import re

with open("frontend/src/pages/Dashboard.jsx", "r") as f:
    content = f.read()

replacement = """function ClientsPanel({ spreadsheetId }) {
  const [clients, setClients] = useState([]);
  const [quotes, setQuotes] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [sheetData, setSheetData] = useState(null);
  const [selectedClient, setSelectedClient] = useState(null);
  const [name, setName] = useState("");
  const token = localStorage.getItem('auth_token');

  useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        const headers = { ...(token ? { Authorization: 'Bearer ' + token } : {}) };
        const [rC, rQ, rI, rS] = await Promise.all([
          fetch(`${API_BASE_URL}/api/clients`, { headers }),
          fetch(`${API_BASE_URL}/api/quotes`, { headers }),
          fetch(`${API_BASE_URL}/api/invoices`, { headers }),
          spreadsheetId ? fetch(`${API_BASE_URL}/api/user/spreadsheet/data`, { headers }) : Promise.resolve(null)
        ]);

        if (rC.ok && mounted) setClients(await rC.json() || []);
        if (rQ.ok && mounted) setQuotes(await rQ.json() || []);
        if (rI.ok && mounted) setInvoices(await rI.json() || []);
        if (rS && rS.ok && mounted) {
           const sData = await rS.json();
           setSheetData(sData.data || {});
        }
      } catch (e) {
        console.warn('clients data fetch error', e.message);
      }
    })();
    return () => { mounted = false; };
  }, [token, spreadsheetId]);

  const createClient = async () => {
    if (!name.trim()) return toast.error("Le nom du client est requis");
    try {
      const r = await fetch(`${API_BASE_URL}/api/clients`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: 'Bearer ' + token } : {}) },
        body: JSON.stringify({ name }),
      });
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || 'Erreur');
      setClients((c) => [data, ...c]);
      setName('');
      toast.success("Client créé avec succès !");
    } catch (e) {
      toast.error('Création client échouée: ' + e.message);
    }
  };

  // Derived data for selected client
  const clientQuotes = quotes.filter(q => q.client_id === selectedClient?.id);
  const clientInvoices = invoices.filter(i => i.client_id === selectedClient?.id);
  
  // Extract meetings from Sheets
  const clientMeetings = [];
  if (selectedClient && sheetData && sheetData["Meetings"]) {
    const rows = sheetData["Meetings"].slice(1); // skip header
    for (const row of rows) {
       const invites = row[3] || "";
       // Match by client email or name
       if ((selectedClient.email && invites.toLowerCase().includes(selectedClient.email.toLowerCase())) ||
           (selectedClient.name && invites.toLowerCase().includes(selectedClient.name.toLowerCase()))) {
          clientMeetings.push({
             date: row[0],
             title: row[1],
             time: row[2],
             invites: row[3]
          });
       }
    }
  }

  return (
    <motion.section initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease: [0.2, 0, 0, 1] }} className="h-full flex flex-col sm:flex-row gap-6">
      
      {/* LEFT PANEL: Client List */}
      <div className="w-full sm:w-1/3 flex flex-col gap-4">
        <div className="glass-panel p-4">
          <h3 className="mb-3 text-xs font-medium uppercase tracking-wider text-md-primary">Nouveau Client</h3>
          <div className="flex gap-2">
            <input value={name} onChange={(e) => setName(e.target.value)} className="input flex-1 text-sm py-1" placeholder="Nom du client..." />
            <button onClick={createClient} className="btn-primary px-3 py-1 text-sm">
              <Plus className="size-4" />
            </button>
          </div>
        </div>
        
        <div className="flex-1 overflow-y-auto pr-2 space-y-2">
          {clients.map(c => (
            <div 
              key={c.id} 
              onClick={() => setSelectedClient(c)}
              className={`list-item-glass cursor-pointer p-3 transition-all duration-300 ${selectedClient?.id === c.id ? 'border-md-primary bg-md-primary/10 scale-[1.02]' : 'hover:border-md-primary/30 hover:bg-white/5'}`}
            >
              <div className="flex items-center gap-3">
                <div className="grid size-8 shrink-0 place-items-center rounded-full bg-md-primary-container text-md-on-primary-container">
                  <UserRound className="size-4" />
                </div>
                <div className="min-w-0">
                  <div className="font-medium text-sm text-md-on-surface truncate">{c.name || c.company || 'Client sans nom'}</div>
                  {c.email && <div className="text-xs text-md-on-surface-variant truncate">{c.email}</div>}
                </div>
              </div>
            </div>
          ))}
          {clients.length === 0 && (
             <div className="text-center p-4 text-sm text-md-on-surface-variant">Aucun client trouvé.</div>
          )}
        </div>
      </div>

      {/* RIGHT PANEL: Master Detail */}
      <div className="w-full sm:w-2/3 flex flex-col h-full overflow-y-auto">
        {!selectedClient ? (
          <div className="m-auto text-center opacity-50 flex flex-col items-center">
             <UserRound className="size-16 mb-4" />
             <p className="text-lg font-medium">Sélectionnez un client pour voir les détails</p>
          </div>
        ) : (
          <AnimatePresence mode="wait">
            <motion.div key={selectedClient.id} initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="space-y-6 pb-20">
              
              {/* Header */}
              <div className="glass-panel relative overflow-hidden">
                 <div className="absolute top-0 right-0 p-8 opacity-5">
                    <UserRound className="size-32" />
                 </div>
                 <h2 className="text-2xl font-semibold text-md-on-surface">{selectedClient.name}</h2>
                 {selectedClient.email && <p className="text-md-on-surface-variant mt-1">{selectedClient.email}</p>}
                 {selectedClient.phone && <p className="text-sm text-md-on-surface-variant mt-1">{selectedClient.phone}</p>}
              </div>

              {/* Meetings */}
              <div>
                 <h3 className="text-sm font-semibold uppercase tracking-wider text-md-primary mb-3 flex items-center gap-2"><Calendar className="size-4" /> Rendez-vous</h3>
                 {clientMeetings.length > 0 ? (
                    <div className="grid gap-3 sm:grid-cols-2">
                       {clientMeetings.map((m, i) => (
                          <div key={i} className="list-item-glass p-3 border-l-4 border-l-md-primary">
                             <div className="font-medium text-sm text-md-on-surface">{m.title || "Meeting"}</div>
                             <div className="text-xs text-md-on-surface-variant mt-1">{m.date} à {m.time}</div>
                             <div className="text-xs text-md-on-surface-variant/70 mt-1 truncate">Avec: {m.invites}</div>
                          </div>
                       ))}
                    </div>
                 ) : (
                    <p className="text-sm text-md-on-surface-variant italic">Aucun rendez-vous trouvé.</p>
                 )}
              </div>

              {/* Quotes / Devis */}
              <div>
                 <h3 className="text-sm font-semibold uppercase tracking-wider text-md-primary mb-3 flex items-center gap-2"><FileText className="size-4" /> Devis (Facture proforma)</h3>
                 {clientQuotes.length > 0 ? (
                    <div className="space-y-4">
                       {clientQuotes.map(q => (
                          <div key={q.id} className="glass-panel p-4">
                             <div className="flex justify-between items-start mb-3 border-b border-white/10 pb-3">
                                <div>
                                   <div className="font-semibold text-md-on-surface">{q.quote_number}</div>
                                   <div className="text-xs text-md-on-surface-variant mt-1">Créé le: {q.created_at ? new Date(q.created_at).toLocaleDateString('fr-FR') : '-'}</div>
                                </div>
                                <div className="text-right">
                                   <div className="text-lg font-bold text-md-primary">{Number(q.total_amount).toFixed(2)} MAD</div>
                                   <div className="text-xs text-md-on-surface-variant">Statut: <span className="uppercase tracking-wider">{q.status}</span></div>
                                </div>
                             </div>
                             
                             <div className="space-y-2">
                                <div className="text-xs font-semibold text-md-on-surface-variant mb-1">Produits / Services :</div>
                                {q.items && q.items.length > 0 ? q.items.map((it, i) => (
                                   <div key={i} className="flex justify-between items-center text-sm bg-white/5 rounded px-3 py-2">
                                      <div className="flex-1">
                                         <span className="font-medium">{it.service_name || it.service_code}</span>
                                         {it.discount > 0 && <span className="ml-2 text-xs bg-green-500/20 text-green-400 px-1 rounded">-{it.discount}%</span>}
                                      </div>
                                      <div className="text-md-on-surface-variant text-right">
                                         {it.quantity} x {Number(it.unit_price).toFixed(2)} MAD
                                      </div>
                                   </div>
                                )) : (
                                   <div className="text-xs opacity-50">Aucun produit détaillé</div>
                                )}
                                <div className="pt-2 mt-2 border-t border-white/5 flex justify-end gap-6 text-xs text-md-on-surface-variant">
                                   <div>Sous-total: {Number(q.subtotal).toFixed(2)} MAD</div>
                                   <div>TVA: {Number(q.tax_total).toFixed(2)} MAD</div>
                                </div>
                             </div>
                          </div>
                       ))}
                    </div>
                 ) : (
                    <p className="text-sm text-md-on-surface-variant italic">Aucun devis trouvé.</p>
                 )}
              </div>

            </motion.div>
          </AnimatePresence>
        )}
      </div>

    </motion.section>
  );
}"""

# Replace the ClientsPanel function entirely
start_idx = content.find("function ClientsPanel() {")
end_idx = content.find("/* ═══════════════════════════════════════════════════════\n   SERVICES PANEL")

if start_idx != -1 and end_idx != -1:
    new_content = content[:start_idx] + replacement + "\n\n" + content[end_idx:]
    with open("frontend/src/pages/Dashboard.jsx", "w") as f:
        f.write(new_content)
    print("Replaced ClientsPanel successfully")
else:
    print("Could not find ClientsPanel bounds")
    
# Now fix the usage of ClientsPanel
with open("frontend/src/pages/Dashboard.jsx", "r") as f:
    c2 = f.read()
c2 = c2.replace("<ClientsPanel />", "<ClientsPanel spreadsheetId={spreadsheetId} />")
with open("frontend/src/pages/Dashboard.jsx", "w") as f:
    f.write(c2)
print("Replaced usage of ClientsPanel")

