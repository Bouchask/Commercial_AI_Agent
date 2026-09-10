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
    <div className="flex flex-col h-full bg-md-surface-container-low overflow-hidden rounded-2xl border border-md-outline-variant/30">
      {/* Header / Tabs */}
      {sheets.length > 1 && (
        <div className="flex items-center gap-1 border-b border-md-outline-variant/30 bg-md-surface p-2 overflow-x-auto">
          {sheets.map(sheet => (
            <button
              key={sheet}
              onClick={() => changeSheet(sheet)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium whitespace-nowrap transition-colors ${
                activeSheet === sheet 
                  ? "bg-md-primary/10 text-md-primary" 
                  : "text-md-on-surface-variant hover:bg-md-primary/5"
              }`}
            >
              {sheet}
            </button>
          ))}
        </div>
      )}
      
      {/* Table Content */}
      <div className="flex-1 overflow-auto bg-white p-2 sm:p-4">
        <table className="min-w-full border-collapse">
          <tbody>
            {data.map((row, rowIndex) => {
              // Ignore completely empty rows
              if (!row || row.every(c => c === "" || c === null || c === undefined)) return null;
              
              return (
                <tr key={rowIndex} className="border-b border-md-outline-variant/10 last:border-0 hover:bg-md-primary/5">
                  {row.map((cell, colIndex) => {
                    // Determine if this cell looks like a header (e.g. bold, top rows)
                    const isHeaderRow = rowIndex < 2 || (rowIndex === 7 && cell !== ""); // Heuristic for our invoice template
                    const isTitle = rowIndex === 0 && colIndex === 0;
                    const isTotal = row[colIndex - 1] && typeof row[colIndex - 1] === 'string' && row[colIndex - 1].includes("Total");
                    
                    return (
                      <td 
                        key={colIndex} 
                        className={`
                          px-3 py-2 text-sm whitespace-nowrap border-r border-md-outline-variant/10 last:border-r-0
                          ${isTitle ? 'text-lg font-bold text-md-primary' : ''}
                          ${isHeaderRow ? 'font-medium text-md-on-surface' : 'text-md-on-surface-variant'}
                          ${isTotal ? 'font-bold text-md-primary bg-md-primary/5' : ''}
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
