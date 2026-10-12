// Lê variáveis de ambiente (.env) e produz credenciais + workflow prontos para importação.
const fs = require('fs');
const [credOut, wfOut] = process.argv.slice(2);
const e = process.env;

const creds = [
  { id: 'cred-mqtt', name: 'Mosquitto local', type: 'mqtt',
    data: { protocol: 'mqtt', host: 'mosquitto', port: 1883, clean: true, ssl: false, passwordless: true } },
  { id: 'cred-gemini', name: 'Gemini', type: 'googlePalmApi',
    data: { host: 'https://generativelanguage.googleapis.com', apiKey: e.GEMINI_API_KEY || '' } },
  { id: 'cred-smtp', name: 'SMTP Gmail', type: 'smtp',
    data: { host: e.SMTP_HOST || 'smtp.gmail.com', port: Number(e.SMTP_PORT || 465), secure: true,
            user: e.SMTP_USER || '', password: e.SMTP_PASS || '', disableStartTls: false } },
];
fs.writeFileSync(credOut, JSON.stringify(creds));

const model = e.GEMINI_MODEL || 'gemini-3.5-flash';
const wf = fs.readFileSync('/seed/workflow.json', 'utf8').replace('__GEMINI_MODEL__', model);
fs.writeFileSync(wfOut, wf);
