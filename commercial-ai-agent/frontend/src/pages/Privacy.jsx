import React from 'react';

export default function Privacy() {
  return (
    <div className="min-h-screen bg-md-background text-md-on-surface p-8 sm:p-16">
      <div className="max-w-3xl mx-auto space-y-6">
        <h1 className="text-3xl font-bold mb-8">Politique de Confidentialité</h1>
        
        <p className="text-sm text-md-on-surface-variant">Dernière mise à jour : 21 Septembre 2026</p>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">1. Introduction</h2>
          <p>
            Bienvenue sur Commercial AI. Nous prenons la protection de vos données très au sérieux. 
            Cette politique explique comment nous collectons, utilisons et protégeons vos informations personnelles.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">2. Données collectées</h2>
          <p>
            Lorsque vous utilisez notre application, nous accédons à :
          </p>
          <ul className="list-disc pl-6 space-y-2">
            <li>Votre adresse e-mail et profil Google (pour l'authentification).</li>
            <li>L'accès à l'envoi d'e-mails via Gmail en votre nom (uniquement les e-mails rédigés et validés par vous-même via l'application).</li>
            <li>L'accès à vos Google Sheets pour enregistrer automatiquement vos devis, factures et clients.</li>
            <li>L'accès à Google Agenda pour vérifier vos disponibilités et programmer des réunions.</li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">3. Utilisation des données</h2>
          <p>
            Vos données sont utilisées exclusivement pour fournir le service Commercial AI :
          </p>
          <ul className="list-disc pl-6 space-y-2">
            <li>L'agent IA analyse les requêtes pour générer des devis et factures.</li>
            <li>Les e-mails sont envoyés à vos clients en votre nom, uniquement avec votre approbation explicite.</li>
            <li>Vos données commerciales (clients, réunions, factures) sont stockées dans votre propre base de données Google Sheets.</li>
          </ul>
          <p>
            <strong>Aucune de vos données n'est revendue à des tiers.</strong>
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">4. Sécurité</h2>
          <p>
            Vos tokens d'accès Google sont chiffrés et stockés de manière sécurisée. Nous utilisons les protocoles OAuth 2.0 standards de Google, ce qui signifie que nous n'avons jamais accès à votre mot de passe Google.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold">5. Vos droits</h2>
          <p>
            Vous pouvez à tout moment révoquer l'accès de l'application à votre compte Google via les paramètres de sécurité de votre compte Google.
          </p>
        </section>

        <div className="pt-8 border-t border-md-outline-variant/30 text-sm text-md-on-surface-variant">
          <a href="/" className="text-md-primary hover:underline">&larr; Retour à l'application</a>
        </div>
      </div>
    </div>
  );
}
