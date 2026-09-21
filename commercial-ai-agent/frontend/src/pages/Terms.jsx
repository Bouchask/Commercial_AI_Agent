import React from 'react';

export default function Terms() {
  return (
    <div className="min-h-screen bg-md-background text-md-on-surface p-8 sm:p-16">
      <div className="max-w-3xl mx-auto space-y-6">
        <h1 className="text-3xl font-bold mb-8">Conditions d'Utilisation</h1>
        
        <p className="text-sm text-md-on-surface-variant">Dernière mise à jour : 21 Septembre 2026</p>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">1. Acceptation des conditions</h2>
          <p>
            En accédant et en utilisant Commercial AI, vous acceptez d'être lié par les présentes conditions d'utilisation. Si vous n'acceptez pas ces conditions, veuillez ne pas utiliser l'application.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">2. Description du service</h2>
          <p>
            Commercial AI est un assistant intelligent conçu pour automatiser les tâches commerciales (création de devis, factures, planification de réunions et envoi d'e-mails) via l'intégration avec les API Google Workspace.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">3. Accès aux API Google</h2>
          <p>
            Pour fonctionner, Commercial AI requiert des accès à votre compte Google (Gmail, Sheets, Calendar). Vous acceptez que l'application agisse en votre nom dans les strictes limites de vos requêtes via l'interface de l'assistant. L'application ne modifiera ou n'enverra jamais de données sans une commande explicite de votre part.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">4. Responsabilité</h2>
          <p>
            Les devis, factures et e-mails générés par l'IA doivent toujours être vérifiés par l'utilisateur avant envoi. Nous déclinons toute responsabilité en cas d'erreurs dans les documents générés ou d'envois non intentionnels causés par une mauvaise utilisation de l'outil.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">5. Résiliation</h2>
          <p>
            Vous pouvez cesser d'utiliser nos services à tout moment en révoquant les accès de Commercial AI depuis les paramètres de votre compte Google.
          </p>
        </section>

        <div className="pt-8 border-t border-md-outline-variant/30 text-sm text-md-on-surface-variant">
          <a href="/" className="text-md-primary hover:underline">&larr; Retour à l'application</a>
        </div>
      </div>
    </div>
  );
}
