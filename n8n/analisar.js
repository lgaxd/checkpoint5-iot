// Regras DETERMINÍSTICAS (o LLM não decide o status). Também valida o dado e mantém o histórico em JSON.
const fs = require('fs');
const ARQ = '/data/historico.json';
// o MQTT Trigger (onlyMessage) entrega o payload dentro de um array; também tratamos string/{message}
let d = $input.first().json;
if (Array.isArray(d)) d = d[0];
if (d && d.message !== undefined && d.id_maquina === undefined) d = d.message;
if (typeof d === 'string') { try { d = JSON.parse(d); } catch (e) { d = {}; } }
d = d || {};

const num = ['temperatura', 'vibracao', 'tensao', 'corrente', 'fator_potencia', 'taxa_producao', 'taxa_producao_esperada'];
const invalidos = num.filter(c => typeof d[c] !== 'number' || !isFinite(d[c]));
if (!d.id_maquina) invalidos.unshift('id_maquina');
// plausibilidade física: sensor com defeito/ruído não vira "decisão inteligente"
if (!invalidos.length) {
  if (d.fator_potencia < 0 || d.fator_potencia > 1) invalidos.push('fator_potencia fora de 0..1');
  if (d.temperatura < -50 || d.temperatura > 300) invalidos.push('temperatura fora de -50..300');
  if (d.vibracao < 0) invalidos.push('vibracao negativa');
  if (d.taxa_producao_esperada <= 0) invalidos.push('taxa_producao_esperada <= 0');
}
if (invalidos.length) {
  return [{ json: { id_maquina: d.id_maquina || 'DESCONHECIDA', situacao: 'DADO_INVALIDO',
    problemas: [], campos_invalidos: invalidos, canais: [] } }];
}

const problemas = [];
let producaoEletrico = false;
if (d.temperatura > 80) problemas.push('Temperatura elevada');
if (d.vibracao > 7) problemas.push('Vibração elevada');
if (d.fator_potencia < 0.70) { problemas.push('Fator de potência baixo'); producaoEletrico = true; }
if (d.taxa_producao < 0.8 * d.taxa_producao_esperada) { problemas.push('Produção abaixo do esperado'); producaoEletrico = true; }

const situacao = problemas.length ? 'ALERTA' : 'NORMAL';
// temperatura/vibração -> Telegram; produção/fator de potência -> Telegram + e-mail
const canais = [];
if (situacao === 'ALERTA') { canais.push('telegram'); if (producaoEletrico) canais.push('email'); }

// histórico simples em JSON
let hist = [];
try { hist = JSON.parse(fs.readFileSync(ARQ, 'utf8')); } catch (e) { hist = []; }
const anteriores = hist.filter(h => h.id_maquina === d.id_maquina).slice(-5);
let variacao = null;
if (anteriores.length) {
  const media = anteriores.reduce((s, h) => s + h.temperatura, 0) / anteriores.length;
  variacao = Math.round(((d.temperatura - media) / media) * 1000) / 10;
}
hist.push({ ts: new Date().toISOString(), id_maquina: d.id_maquina, temperatura: d.temperatura,
  vibracao: d.vibracao, fator_potencia: d.fator_potencia, taxa_producao: d.taxa_producao, situacao });
try { fs.writeFileSync(ARQ, JSON.stringify(hist.slice(-100), null, 1)); } catch (e) {}

return [{ json: { ...d, situacao, problemas, canais,
  variacao_temp_pct_vs_ultimas_leituras: variacao, leituras_anteriores: anteriores.length } }];
