import React, { useState, useEffect } from "react";
import * as XLSX from "xlsx";

export function ExcelViewer({ url, title }) {
  const [data, setData] = useState([]);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [activeSheet, setActiveSheet] = useState("");
  const [sheets, setSheets] = useState([]);

  useEffect(() => {
    let active = true;
    const fetchExcel = async () => {
      try {
        const token = localStorage.getItem('auth_token');
        const res = await fetch(url, {
          headers: token ? { Authorization: `Bearer ${token}` } : {}
        });
        
        if (!res.ok) throw new Error("Erreur de chargement du fichier Excel");
        
        const arrayBuffer = await res.arrayBuffer();
        const workbook = XLSX.read(arrayBuffer, { type: 'array' });
        
        if (active) {
          const sheetNames = workbook.SheetNames;
          setSheets(sheetNames);
          
          if (sheetNames.length > 0) {
            const firstSheetName = sheetNames[0];
            setActiveSheet(firstSheetName);
            const worksheet = workbook.Sheets[firstSheetName];
            const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1, defval: "" });
            setData(jsonData);
          }
          setIsLoading(false);
        }
      } catch (err) {
        if (active) {
          setError(err.message);
          setIsLoading(false);
        }
      }
    };
    
    fetchExcel();
    return () => { active = false; };
  }, [url]);

  const changeSheet = (sheetName) => {
    try {
      const token = localStorage.getItem('auth_token');
      fetch(url, {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      }).then(res => res.arrayBuffer()).then(arrayBuffer => {
        const workbook = XLSX.read(arrayBuffer, { type: 'array' });
        const worksheet = workbook.Sheets[sheetName];
        const jsonData = XLSX.utils.sheet_to_json(worksheet, { header: 1, defval: "" });
        setData(jsonData);
        setActiveSheet(sheetName);
      });
    } catch (e) {
      console.error(e);
    }
  };

  if (error) return <div className="p-4 text-md-error text-xs flex items-center justify-center h-full bg-md-error/10 rounded-2xl">Erreur: {error}</div>;
  if (isLoading) return <div className="p-4 text-md-on-surface-variant text-xs flex items-center justify-center h-full">Chargement du fichier Excel...</div>;
  if (data.length === 0) return <div className="p-4 text-md-on-surface-variant text-xs flex items-center justify-center h-full">Document vide.</div>;

  return (
    <div className="flex flex-col h-full bg-bg-card overflow-hidden rounded-2xl border border-border">
      {/* Header / Tabs */}
      {sheets.length > 1 && (
        <div className="flex items-center gap-1.5 border-b border-border bg-bg-elevated/80 p-2.5 overflow-x-auto">
          {sheets.map(sheet => (
            <button
              key={sheet}
              onClick={() => changeSheet(sheet)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all ${
                activeSheet === sheet 
                  ? "bg-accent-1 text-white shadow-sm shadow-accent-1/30" 
                  : "text-text-secondary hover:text-text-primary hover:bg-white/5"
              }`}
            >
              {sheet}
            </button>
          ))}
        </div>
      )}
      
      {/* Table Content */}
      <div className="flex-1 overflow-auto bg-bg-card p-2 sm:p-4">
        <table className="min-w-full border-collapse">
          <tbody>
            {data.map((row, rowIndex) => {
              // Ignore completely empty rows
              if (!row || row.every(c => c === "" || c === null || c === undefined)) return null;
              
              return (
                <tr key={rowIndex} className="border-b border-border/50 last:border-0 hover:bg-white/[0.03]">
                  {row.map((cell, colIndex) => {
                    // Determine if this cell looks like a header (e.g. bold, top rows)
                    const isHeaderRow = rowIndex < 2 || (rowIndex === 7 && cell !== ""); // Heuristic for our invoice template
                    const isTitle = rowIndex === 0 && colIndex === 0;
                    const isTotal = row[colIndex - 1] && typeof row[colIndex - 1] === 'string' && row[colIndex - 1].includes("Total");
                    
                    return (
                      <td 
                        key={colIndex} 
                        className={`
                          px-3 py-2 text-sm whitespace-nowrap border-r border-border/30 last:border-r-0
                          ${isTitle ? 'text-lg font-bold text-accent-1' : ''}
                          ${isHeaderRow ? 'font-semibold text-text-primary bg-bg-elevated/40' : 'text-text-secondary'}
                          ${isTotal ? 'font-bold text-accent-1 bg-accent-1/10' : ''}
                          ${typeof cell === 'number' ? 'text-right' : 'text-left'}
                        `}
                      >
                        {typeof cell === 'number' && !Number.isInteger(cell) ? cell.toFixed(2) : cell}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
