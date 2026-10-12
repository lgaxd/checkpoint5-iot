// Ferramenta MCP: consulta o histórico da máquina (JSON local)
const fs = require('fs');
let hist = [];
try { hist = JSON.parse(fs.readFileSync('/data/historico.json', 'utf8')); } catch (e) {}
const id = String(query || '').trim();
const itens = hist.filter(h => !id || h.id_maquina === id).slice(-10);
if (!itens.length) return 'Sem histórico para ' + (id || 'a máquina') + '.';
const temps = itens.map(h => h.temperatura);
const media = temps.reduce((a, b) => a + b, 0) / temps.length;
const dp = Math.sqrt(temps.reduce((a, b) => a + (b - media) ** 2, 0) / temps.length);
return JSON.stringify({ leituras: itens.length, temperatura_media: +media.toFixed(1),
  temperatura_desvio_padrao: +dp.toFixed(2), ultimas: itens });
