import datetime
from flask import render_template_string

WAITING_ROOM_HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Salle d'attente - {{ meeting.title }}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-gradient: linear-gradient(135deg, #090d16 0%, #0f172a 50%, #1e1b4b 100%);
            --card-bg: rgba(30, 41, 59, 0.7);
            --card-border: rgba(255, 255, 255, 0.1);
            --primary: #6366f1;
            --primary-glow: rgba(99, 102, 241, 0.35);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --accent: #38bdf8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-gradient);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1.5rem;
        }
        .container {
            max-width: 580px;
            width: 100%;
            background: var(--card-bg);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid var(--card-border);
            border-radius: 24px;
            padding: 2.5rem;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5), 0 0 40px var(--primary-glow);
            text-align: center;
            animation: fadeIn 0.6s ease-out;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(12px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 14px;
            border-radius: 9999px;
            background: rgba(99, 102, 241, 0.15);
            border: 1px solid rgba(99, 102, 241, 0.3);
            color: #818cf8;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 1.5rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #f59e0b;
            box-shadow: 0 0 10px #f59e0b;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.4; }
        }
        h1 {
            font-size: 1.85rem;
            font-weight: 800;
            margin-bottom: 0.75rem;
            background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        p.subtitle {
            color: var(--text-muted);
            font-size: 1rem;
            line-height: 1.5;
            margin-bottom: 2rem;
        }
        .countdown-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-bottom: 2rem;
        }
        .time-box {
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.06);
            border-radius: 16px;
            padding: 1.25rem 0.5rem;
        }
        .time-value {
            font-size: 2rem;
            font-weight: 800;
            color: var(--accent);
            line-height: 1;
            margin-bottom: 4px;
            font-variant-numeric: tabular-nums;
        }
        .time-label {
            font-size: 0.72rem;
            text-transform: uppercase;
            color: var(--text-muted);
            letter-spacing: 0.05em;
            font-weight: 600;
        }
        .info-card {
            background: rgba(15, 23, 42, 0.4);
            border-radius: 14px;
            padding: 1rem 1.25rem;
            text-align: left;
            margin-bottom: 1.5rem;
            font-size: 0.9rem;
            border-left: 3px solid var(--primary);
        }
        .info-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.5rem;
        }
        .info-row:last-child { margin-bottom: 0; }
        .info-key { color: var(--text-muted); }
        .info-val { color: var(--text-main); font-weight: 600; }
        .note {
            font-size: 0.85rem;
            color: var(--text-muted);
            line-height: 1.4;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="badge">
            <span class="status-dot"></span>
            Salle sécurisée &bull; En attente
        </div>
        <h1>{{ meeting.title }}</h1>
        <p class="subtitle">Cette salle de réunion est configurée pour s'ouvrir automatiquement à l'heure convenue.</p>
        
        <div class="countdown-grid">
            <div class="time-box">
                <div id="days" class="time-value">00</div>
                <div class="time-label">Jours</div>
            </div>
            <div class="time-box">
                <div id="hours" class="time-value">00</div>
                <div class="time-label">Heures</div>
            </div>
            <div class="time-box">
                <div id="minutes" class="time-value">00</div>
                <div class="time-label">Minutes</div>
            </div>
            <div class="time-box">
                <div id="seconds" class="time-value">00</div>
                <div class="time-label">Secondes</div>
            </div>
        </div>

        <div class="info-card">
            <div class="info-row">
                <span class="info-key">Ouverture de la salle :</span>
                <span class="info-val">{{ active_from_str }}</span>
            </div>
            <div class="info-row">
                <span class="info-key">Statut :</span>
                <span class="info-val" style="color: #f59e0b;">Verrouillée jusqu'au créneau</span>
            </div>
        </div>

        <p class="note">
            💡 Restez sur cette page : l'accès à la visioconférence sera déverrouillé et actualisé dès l'ouverture du créneau.
        </p>
    </div>

    <script>
        let remainingSeconds = {{ seconds_remaining }};

        function updateCountdown() {
            if (remainingSeconds <= 0) {
                document.getElementById('days').innerText = '00';
                document.getElementById('hours').innerText = '00';
                document.getElementById('minutes').innerText = '00';
                document.getElementById('seconds').innerText = '00';
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
                return;
            }

            const d = Math.floor(remainingSeconds / 86400);
            const h = Math.floor((remainingSeconds % 86400) / 3600);
            const m = Math.floor((remainingSeconds % 3600) / 60);
            const s = Math.floor(remainingSeconds % 60);

            document.getElementById('days').innerText = String(d).padStart(2, '0');
            document.getElementById('hours').innerText = String(h).padStart(2, '0');
            document.getElementById('minutes').innerText = String(m).padStart(2, '0');
            document.getElementById('seconds').innerText = String(s).padStart(2, '0');

            remainingSeconds--;
        }

        updateCountdown();
        setInterval(updateCountdown, 1000);
    </script>
</body>
</html>
"""

ACTIVE_ROOM_HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Réunion en cours - {{ meeting.title }}</title>
    <meta http-equiv="refresh" content="2;url={{ meeting.meet_url }}">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-gradient: linear-gradient(135deg, #064e3b 0%, #0f172a 50%, #065f46 100%);
            --card-bg: rgba(30, 41, 59, 0.75);
            --card-border: rgba(52, 211, 153, 0.2);
            --primary: #10b981;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background: var(--bg-gradient);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1.5rem;
        }
        .container {
            max-width: 540px;
            width: 100%;
            background: var(--card-bg);
            backdrop-filter: blur(20px);
            border: 1px solid var(--card-border);
            border-radius: 24px;
            padding: 2.5rem;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5), 0 0 40px rgba(16, 185, 129, 0.2);
            text-align: center;
        }
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 14px;
            border-radius: 9999px;
            background: rgba(16, 185, 129, 0.15);
            border: 1px solid rgba(16, 185, 129, 0.3);
            color: #34d399;
            font-size: 0.85rem;
            font-weight: 700;
            margin-bottom: 1.5rem;
            text-transform: uppercase;
        }
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #10b981;
            box-shadow: 0 0 10px #10b981;
        }
        h1 {
            font-size: 1.85rem;
            font-weight: 800;
            margin-bottom: 0.75rem;
        }
        p {
            color: var(--text-muted);
            margin-bottom: 2rem;
            line-height: 1.5;
        }
        .btn-join {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            background: linear-gradient(135deg, #10b981 0%, #059669 100%);
            color: white;
            padding: 1rem 2rem;
            border-radius: 14px;
            font-weight: 700;
            font-size: 1.05rem;
            text-decoration: none;
            box-shadow: 0 10px 20px -5px rgba(16, 185, 129, 0.4);
            transition: transform 0.2s ease;
        }
        .btn-join:hover {
            transform: translateY(-2px);
        }
        .spinner {
            width: 32px;
            height: 32px;
            border: 3px solid rgba(255, 255, 255, 0.1);
            border-top-color: #10b981;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 1.5rem auto 0;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="badge">
            <span class="status-dot"></span>
            Salle active maintenant
        </div>
        <h1>{{ meeting.title }}</h1>
        <p>Le créneau est actuellement ouvert. Vous êtes redirigé vers la visioconférence...</p>
        
        <a href="{{ meeting.meet_url }}" class="btn-join">
            <span>Rejoindre la réunion</span>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path d="M5 12h14M12 5l7 7-7 7"/>
            </svg>
        </a>

        <div class="spinner"></div>
    </div>
</body>
</html>
"""

EXPIRED_ROOM_HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Réunion terminée - {{ meeting.title }}</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-gradient: linear-gradient(135deg, #1e1b4b 0%, #0f172a 100%);
            --card-bg: rgba(30, 41, 59, 0.7);
            --card-border: rgba(239, 68, 68, 0.2);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background: var(--bg-gradient);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1.5rem;
        }
        .container {
            max-width: 520px;
            width: 100%;
            background: var(--card-bg);
            backdrop-filter: blur(20px);
            border: 1px solid var(--card-border);
            border-radius: 24px;
            padding: 2.5rem;
            text-align: center;
            box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
        }
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 6px 14px;
            border-radius: 9999px;
            background: rgba(239, 68, 68, 0.15);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: #f87171;
            font-size: 0.85rem;
            font-weight: 700;
            margin-bottom: 1.5rem;
            text-transform: uppercase;
        }
        h1 {
            font-size: 1.85rem;
            font-weight: 800;
            margin-bottom: 0.75rem;
        }
        p {
            color: var(--text-muted);
            margin-bottom: 1.5rem;
            line-height: 1.5;
        }
        .closure-info {
            background: rgba(15, 23, 42, 0.5);
            border-radius: 12px;
            padding: 1rem;
            font-size: 0.9rem;
            color: var(--text-muted);
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="badge">Salle clôturée</div>
        <h1>{{ meeting.title }}</h1>
        <p>Cette réunion est arrivée à son terme et la salle vidéo a été désactivée conformément au créneau sélectionné.</p>
        <div class="closure-info">
            Fermeture effective : <strong>{{ active_until_str }}</strong>
        </div>
    </div>
</body>
</html>
"""

NOT_FOUND_HTML = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Réunion introuvable</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;700&display=swap" rel="stylesheet">
    <style>
        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background: #0f172a;
            color: #f8fafc;
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 1rem;
        }
        .card {
            background: #1e293b;
            padding: 2.5rem;
            border-radius: 20px;
            max-width: 460px;
            border: 1px solid rgba(255,255,255,0.1);
        }
        h1 { font-size: 1.5rem; margin-bottom: 0.75rem; color: #ef4444; }
        p { color: #94a3b8; font-size: 0.95rem; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Identifiant de réunion introuvable</h1>
        <p>Le lien demandé ne correspond à aucune réunion active ou enregistrée dans le système.</p>
    </div>
</body>
</html>
"""
